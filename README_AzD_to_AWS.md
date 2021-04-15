Deploying python as lambda functions via AzD
AzD:
	The build pipeline monitors the repo for changes and builds the projects on an ubuntu VM by:
		installing python 3.8, pip, pipenv, docker, and poetry
		injecting the API key into the encv/template.yml
		running make clean / make build
			This outputs :
			Build Succeeded
			Built Artifacts  : .aws-sam/build
			Built Template   : .aws-sam/build/template.yaml
			Built toml		 : .aws-sam/build.toml
		
		concat the generated toml with the static toml (codepipeline needs a version number)
			cat .aws-sam/build.toml >> sam.toml
		
		running sam package --config-file sam.toml --s3-bucket cdphe-covidpython-t-release --force-upload --template-file .aws-sam/build/template.yaml --region us-east-1 --output-template-file cdphe-covidpython-t-release.yaml
			This command sends 5 artifacts up to an S3 bucket - they are all hash names (ex. 613f80d7988e73a89f521939235e0df1 )
			and generates a template file - cdphe-covidpython-t-release.yaml that refers to the functions by hash name

		generate a zip archive/build artifact with buildspec.yml cdphe-covidpython-t-release.yaml sam.toml inside

	The release pipeline:
		pulls in the zip archive, renames it to what aws codepipline is expecting (cdphe-covidpython-t-release.zip)
		uploads the zip file to S3
		monitors the codebuild on AWS (commands executed are in the buildspec.yml file - this is where the sam deploy command runs)
			this will return a success/failure
			
AWS:
	Codebuild picks up the zip file from S3 bucket and executes commands in buildspec.yml
	Changes deployed to Lambda, Step Functions, State Machine
	Deployment logging available in Codebuild
	Minimal runtime logging available in Cloudwatch
		Warning logged - does not affect functionality
		/var/task/google/cloud/bigquery/client.py:444: UserWarning: Cannot create BigQuery Storage client, the dependency google-cloud-bigquery-storage is not installed.

