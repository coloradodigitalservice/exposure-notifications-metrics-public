# ENCV To DB

A Cloud function to take as input data from ENCV and import it into BigQuery

## Run - Poetry

1. Install Poetry using the instructions at https://python-poetry.org/docs/ . On Mac OSX, this will be:
   ```sh
   curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
   source $HOME/.poetry/env
   ```
   Otherwise:
   ```sh
   pip3 install poetry
   ```
2. Download data from ENCV manually and store in a file called data.json:
   ```bash
   curl -k https://adminapi.encv.org/api/stats/realm.json \
   --header "x-api-key: $ENCV_API_KEY" \
   --header "content-type: application/json" \
   --header "accept: application/json" > data.json
   ```
3. Run the app with `poetry run python main.py`

## Run - Pack

If you're on a machine with a different architecture, or want environment consistency, Google provides a tool named `pack` to create container images directly from sourcecode and without a dockerfile. To use it:

1. Install docker ([here](https://docs.docker.com/get-docker/))
2. Download /install the `pack` cli tool ([here](https://buildpacks.io/docs/tools/pack/))
3. Install `jq` for manipulating json ([here](https://stedolan.github.io/jq/download/))
4. Build your container image with:
   ```sh
      pack build \
       --builder gcr.io/buildpacks/builder:v1 \
       --env GOOGLE_FUNCTION_SIGNATURE_TYPE=http \
       --env GOOGLE_FUNCTION_TARGET=encv_to_db \
       encv_to_db
   ```
5. Run the image with:
   ```sh
   docker run --rm -p 8080:8080 --env "GOOGLE_APPLICATION_CREDENTIALS_JSON=$(cat service.json)" encv_to_db
   ```
   where `service.json` is your google service account credentials
6. curl with the data from ENCV, passing it to `jq` to get the `statistics` property:
   ```sh
   curl -X POST -H 'Content-Type: application/json'  -d "$(cat data.json| jq '.statistics')" localhost:8080
   ```

## Deploy

1. Create a secret called `ENCV_api_key` in [secret manager](https://console.cloud.google.com/security/secret-manager)
2. Create a BigQuery dataset called `encv` in the [BigQuery Console](https://console.cloud.google.com/bigquery).
3. Deploy the cloud function with `gcloud functions deploy encv_to_db --runtime python38 --trigger-http --allow-unauthenticated --timeout=240`
4. Deploy the workflow with gcloud workflows deploy YOUR_WORKFLOW_NAME --source=workflow.yaml
5. Execute the workflow with `gcloud workflows execute YOUR_WORKFLOW_NAME`
6. Monitor on the Workflows [console](https://console.developers.google.com/workflows), or with the command given following deploy, e.g. `gcloud workflows executions describe EXECUTION_GUID --workflow YOUR_WORKFLOW_NAME --location us-central1`
