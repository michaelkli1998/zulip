import os
import sys
import subprocess
import string
import random

bashfile=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
bashfile='/tmp/'+bashfile+'.sh'

# check for the venv
from lib import sanity_check

sanity_check.check_venv(__file__)

f = open(bashfile, 'w')
s = """#!/usr/bin/env bash
set -e

color_message() {
    local color_code="$1" message="$2"
    printf '\\e[%sm%s\\e[0m\\n' "$color_code" "$message" >&2
}

loglevel=()

usage() {
    cat <<EOF
usage:
  --help, -h                   show this help message and exit
  --loglevel=LEVEL, -L LEVEL   log level (default: ERROR)
  --skip-check-links           skip checking of links
  --skip-external-links        skip checking of external links
EOF
}

args="$(getopt -o hL: --long help,loglevel:,skip-check-links,skip-external-links -- "$@")" \\
    || {
        usage >&2
        exit 1
    }
eval "set -- $args"
while true; do
    case "$1" in
        -h | --help)
            usage
            exit 0
            ;;
        -L | --loglevel)
            loglevel=("$1" "$2")
            shift 2
            ;;
        --skip-check-links)
            skip_check_links=1
            shift
            ;;
        --skip-external-links)
            skip_external_links=1
            shift
            ;;
        --)
            shift
            break
            ;;
        *) exit 1 ;;
    esac
done

cd "$(dirname "$0")"/../docs

# collapse_navigation is set to False in conf.py to improve sidebar navigation for users.
# However, we must change its value to True before we begin testing links.
# Otherwise, sphinx would generate a large number of links we don't need to test.
# The crawler would take a very long time to finish and TravisCI would fail as a result.
make clean html O='-D html_theme_options.collapse_navigation=True'

err=0

check() {
    if "$@"; then
        color_message 92 "Passed!"
    else
        color_message 91 "Failed!"
        err=1
    fi
}

color_message 94 "Validating HTML..."
check java -jar ../node_modules/vnu-jar/build/dist/vnu.jar \\
    --filterfile ../tools/documentation.vnufilter \\
    --skip-non-html \\
    _build/html

if [ -n "$skip_check_links" ]; then
    color_message 94 "Skipped testing links in documentation."
else
    cd ../tools/documentation_crawler
    if [ -n "$skip_external_links" ]; then
        color_message 94 "Testing only internal links in documentation..."
        check scrapy crawl_with_status documentation_crawler -a skip_external=set "${loglevel[@]}"
        # calling crawl directly as parameter needs to be passed
    else
        color_message 94 "Testing links in documentation..."
        check scrapy crawl_with_status documentation_crawler "${loglevel[@]}"
    fi
fi

exit "$err"
"""
f.write(s)
f.close()
os.chmod(bashfile, 0o755)
bashcmd=bashfile
for arg in sys.argv[1:]:
  bashcmd += ' '+arg
subprocess.call(bashcmd, shell=True)
