# Jobmon GUI

A GUI to visualize Jobmon Workflows.

## Overview

This application uses React, FastApi, and Bootstrap.

## Testing Locally

### Deploying the Jobmon Server Backend Locally

To deploy the Jobmon Server Backend locally:

1. Create your own local `./.env` file if you don't have it already (see `./.env.example`).
2. Open a terminal.
3. Make a conda environment and activate it.
4. Install `nox` by running `conda install conda-forge::nox`.
5. Navigate to the top of the Jobmon repository.
6. Run `nox -s build_gui_test_env`.
7. Run `conda activate ./.nox/build_gui_test_env`.
8. Run `pip install -e ./jobmon_core ./jobmon_client ./jobmon_server`.
9. Run `python jobmon_gui/local_testing/main.py`
    - This command will spin up a local version of the Jobmon Server, running on 127.0.0.1:8070 by default. You can then configure the React app to point to this URL for testing purposes.
10. Run `python jobmon_gui/local_testing/create_wfs.py`
    - This command will continuously create workflows in the Jobmon Server. You can then view these workflows in the React app. See the `create_wfs.py` script for more information on how to customize the workflow creation process.

### Deploying the Jobmon GUI Frontend Locally

To deploy the Jobmon GUI Frontend locally:

1. Open a new terminal
2. Install bun
3. Navigate to the jobmon_gui subdirectory
4. Run `bun install`
5. Run `bun start`

You can then access the site at: http://localhost:3000
