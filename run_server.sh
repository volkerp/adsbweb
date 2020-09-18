export FLASK_APP=app
export FLASK_ENV=development
export TRACKSDIR=$(pwd)/tracks

python3 -m flask run --host=0.0.0.0


