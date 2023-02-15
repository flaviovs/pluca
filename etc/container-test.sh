if [ ! -f /.dockerenv ]; then
    echo "$0: Not a container" 1>&2
    exit 1
fi

if [ $(whoami) = "root" ]; then
    echo "$0: Must not be root" 1>&2
    exit 1
fi

set -e

rm -rf /tmp/app
cp --recursive /app /tmp

cd /tmp/app

git clean --quiet --force -dX

PATH=${PATH}:${HOME}/.local/bin
export PATH

pip --quiet install --requirement=requirements-dev.txt

if [ "$PGDATABASE" != "" ] && ! $(psql --command '' > /dev/null 2>&1); then
    createdb
fi

mysql -u root --execute="CREATE DATABASE IF NOT EXISTS $MYSQL_DATABASE"

python --version

task lint
task test
