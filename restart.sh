set -eu

# stop.sh
docker compose -p love-simulator down "$@"

# run.sh
docker compose -p love-simulator up --build -d "$@"