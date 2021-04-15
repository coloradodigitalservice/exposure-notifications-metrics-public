# Functions

This directory contains the functions referenced by the state machine. Each is a self-contained project, which you can open, run, and run tests for with VSCode directly.

Alternatively, you can open `workspace.code-workspace` and see all four functions at once. With the workspace open, you can run code / run tests on that code for each of the four current functions - the workspace will automatically pick up on the virtual environments referenced in the poetry files.

## Dependencies

Each function uses Poetry to manage dependencies, run tests, and package. Unfortunately SAM requires a requirements.txt file.
The `pyproject.toml` files in each function directory is meant to be the source of truth; the requirements.txt files are generated from this.

To create a `requirements.txt` file, you can do :

```sh
poetry export --without-hashes -f requirements.txt -o requirements.txt --with-credentials
```

You can alternatively run `make build.requirements` from the top-level directory to create all `requirements.txt` files at once.

Note: you should not manually alter the requirements.txt file directly. Instead, run `poetry add X` to add dependency X to your project, then run the above `export` or `make` comamnds!
This is why `requirements.txt` has been added to the `.gitignore` file.

## Build

You can build each service by `cd`ing into the service directory, then running `poetry install`, which will create a virtual environment at `./.venv` and install all required dependencies.
Alternatively do this for all targets at the top level with the makefile target `make build.local`

## Run

You can run each service by `cd`ing into the service directory, then running `poetry run python app.py`, after having run `poetry install` as above

## Test

You can test each service by `cd`ing into the service directory, then running `poetry run pytest --capture=no --verbose --cov=app --cov-report term-missing`.
Alternatively do this for all targets at the top level with the makefile target `make test.local`

## Deploy

To deploy infrastructure in this project:

1. From the top level directory, run `make deploy.guided` the first time, then `make deploy` subsequent times. Under the hood this will run `sam build.requirements` to create the `requirements.txt` files, and `sam build` to build the local aws project, then deploy it.
2. As part of `sam deploy.guided`, you will be prompted to add a value for the `ENCV_API_KEY` parameter - paste your value from encv.org when prompted
3. _Important!_ The project creates a secrets manager storage, but does not populate the `GOOGLECREDENTIAL` secret itself. You will need to go to SecretsManager and paste the contents of your `secrets.json` file from the service account associated with your GCP project into the secret with a name matching the one you choose to supply as GOOGLE_APPLICATION_CREDENTIALS_SECRET.
