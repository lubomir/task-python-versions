import logging
if __name__ == '__main__':
    # Set up logging ASAP to see potential problems during import.
    # Don't set it up when not running as the main script, someone else handles
    # that then.
    logging.basicConfig()

import os
import rpm
from libtaskotron import check

log = logging.getLogger('python_versions_check')
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())

NEVRS_STARTS = {
    2: (b'python(abi) = 2.',),
    3: (b'python(abi) = 3.',)
}

NAME_STARTS = {
    2: (
        b'python-',
        b'python2',
        b'/usr/bin/python2',
        b'libpython2',
        b'pygtk2',
        b'pygobject2',
        b'pycairo',
        b'py-',
    ),
    3: (
        b'python3',
        b'/usr/bin/python3',
        b'libpython3',
        b'system-python'
    )
}

NAME_EXACTS = {
    2: (
        b'/usr/bin/python',
        b'python',
    )
} 


def python_versions_check(path):
    '''
    For the binary RPM in path, report back what Python
    versions it depends on
    '''
    ts = rpm.TransactionSet()
    with open(path, 'rb') as fdno:
        hdr = ts.hdrFromFdno(fdno)
    
    py_versions = set()

    for nevr in hdr[rpm.RPMTAG_REQUIRENEVRS]:
        for py_version, starts in NEVRS_STARTS.items():
            for start in starts:
                if nevr.startswith(start):
                    log.debug('Found dependency {}'.format(nevr.decode()))
                    log.debug('Requires Python {}'.format(py_version))
                    py_versions.add(py_version)
                    break

    for name in hdr[rpm.RPMTAG_REQUIRENAME]:
        for py_version, starts in NAME_STARTS.items():
            if py_version not in py_versions:
                for start in starts:
                    if name.startswith(start):
                        log.debug('Found dependency {}'.format(name.decode()))
                        log.debug('Requires Python {}'.format(py_version))
                        py_versions.add(py_version)
                        break
        for py_version, exacts in NAME_EXACTS.items():
            if py_version not in py_versions:
                if name in exacts:
                    log.debug('Found dependency {}'.format(name.decode()))
                    log.debug('Requires Python {}'.format(py_version))
                    py_versions.add(py_version)

    return py_versions


def run(koji_build, workdir='.', artifactsdir=None):
    '''The main method to run from Taskotron'''
    workdir = os.path.abspath(workdir)

    # find files to run on
    files = sorted(os.listdir(workdir))
    rpms = []
    for file_ in files:
        path = os.path.join(workdir, file_)
        if file_.endswith('.src.rpm'):
            log.debug('Ignoring srpm: {}'.format(path))
        elif file_.endswith('.rpm'):
            rpms.append(path)
        else:
            log.debug('Ignoring non-rpm file: {}'.format(path))
            log.debug('Ignoring non-rpm file: %s', path)

    outcome = 'PASSED'
    bads = []

    if not rpms:
        log.warn('No binary rpm files found in: {}'.format(workdir))
    for path in rpms:
        log.debug('Checking {}'.format(path))
        py_versions = python_versions_check(path)
        if len(py_versions) == 0:
            log.info('{} does not require Python, that\'s OK'.format(path))
        elif len(py_versions) == 1:
            py_version = next(iter(py_versions))
            log.info('{} requires Python {} only, that\'s OK'
                     .format(path, py_version))
        else:
            log.error('{} requires both Python 2 and 3, that\'s usually bad.'
                      .format(path))
            outcome = 'FAILED'
            bads.append(path)

    detail = check.CheckDetail(koji_build, check.ReportType.KOJI_BUILD, outcome)
    if bads:
        s = 's' if len(bads) else ''
        detail.note = ('{} require{} both Pythons, '
                       'if you think that\'s false or intentional, '
                       'file a bug against TODO'.format(','.join(bads), s))
    else:
        detail.note = 'no problems found'

    summary = 'python_versions_check {} for {} ({})'.format(
                  outcome, koji_build, detail.note)
    log.info(summary)

    output = check.export_YAML(detail)
    return output


if __name__ == '__main__':
    run('test')