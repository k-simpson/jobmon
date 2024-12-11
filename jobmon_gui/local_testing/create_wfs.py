import argparse
import os
import random
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import subprocess
from time import sleep
from pathlib import Path

import numpy as np

# from jobmon.server.web.config import get_jobmon_config
# from jobmon.server.web.db_admin import get_engine_from_config
# from jobmon.server.web.models.task_instance import TaskInstance


def parse_arguments() -> argparse.Namespace:
    """
    Function to parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    # Create the parser
    parser = argparse.ArgumentParser(description="Example script with optional arguments.")

    # Add the first optional argument
    parser.add_argument('--server-url',
                        type=str,
                        help="Description for the first optional argument.",
                        default="http://localhost:8070/api/v3")

    # Add the second optional argument
    parser.add_argument('--wf',
                        type=int,
                        help="Number of workflows to create. 0 means continuesly creating workflows.",
                        default=0)

    # Add the --wf-type argument with limited options
    parser.add_argument(
        '--wf-type',
        type=str,
        help="Type of workflows: simple, tired, or random.",
        choices=["simple", "tired", "random", "usage_data"],  # Specify the allowed values
        default="simple"  # Set the default value
    )

    # Add the --num-tasks argument
    parser.add_argument(
        '--num-tasks',
        type=int,
        help="Number of tasks to create in each workflow.",
        default=5
    )

    # Parse the arguments
    return parser.parse_args()


def generate_usage_data(num_tasks: int, max_id: int) -> list[dict]:
    """
    Generate random distributions for resource usage metrics to update task_instance rows.
    
    Args:
        num_tasks (int): Number of tasks to generate data for.
        max_id (int): Starting ID to update rows.

    Returns:
        list[dict]: List of dictionaries containing generated data for each task.
    """
    # Wallclock: Log-normal distribution
    wallclock = np.random.lognormal(mean=3.9, sigma=0.5, size=num_tasks).astype(int)

    # maxrss: Normal distribution
    maxrss = np.clip(np.random.normal(loc=500, scale=100, size=num_tasks), a_min=100, a_max=None).astype(int)

    # maxpss: Slightly higher than maxrss with some randomness
    maxpss = np.clip(maxrss + np.random.normal(loc=50, scale=25, size=num_tasks), a_min=100, a_max=None).astype(int)

    # CPU: Bimodal distribution
    cpu_modes = np.random.choice([0.2, 1.0], size=num_tasks, p=[0.6, 0.4])
    cpu_noise = np.random.uniform(low=-0.05, high=0.05, size=num_tasks)
    cpu = np.clip(cpu_modes + cpu_noise, 0.1, 1.0)

    return [
        {
            "id": int(row_id),
            "usage_str": f"fake_usage_str_{row_id}",
            "wallclock": int(wallclock[i]),
            "maxrss": int(maxrss[i]),
            "maxpss": int(maxpss[i]),
            "cpu": float(cpu[i]),
        }
        for i, row_id in enumerate(range(max_id + 1, max_id + 1 + num_tasks))
    ]


def create_simple_wf():
    """Use the task_generator_wf.py script to create a simple workflow."""
    wf_script_path = Path(__file__).parent.parent.parent / "tests/worker_node/task_generator_wf.py"
    # Run the command and wait for it to finish
    result = subprocess.check_output(["python", str(wf_script_path), "1"])
    # This line will only run after the command above finishes
    print("Simple workflow completed!")


def create_tired_wf():
    """Use dummy cluster to create a fake tired workflow."""
    from jobmon.client.api import Tool
    tool = Tool("multiprocess")
    C = "multiprocess"
    Q = "null.q"
    tt = tool.get_task_template(
        template_name="tired_task1",
        command_template="sleep {arg} || true || {arg_filler}",
        node_args=["arg"],
        task_args=["arg_filler"]
    )
    tt2 = tool.get_task_template(
        template_name="tired_task2",
        command_template="echo {arg}",
        node_args=["arg"]
    )
    # get a randome number between 1 and 10
    num_tasks = random.randint(1, 10)
    tier1 = []
    for i in range(num_tasks):
        task = tt.create_task(
            name=f"tired_task_{i}",
            arg=i,
            arg_filler=f"Task {i} is tired",
            compute_resources={"queue": Q, "num_cores": 1},
        )
        tier1.append(task)
    task = tt2.create_task(
        name=f"tired_task_second_tier",
        arg="I am the last task",
        upstream_tasks=tier1,
        compute_resources={"queue": Q, "num_cores": 1},
    )
    tasks = tier1 + [task]
    wf = tool.create_workflow(
        name=f"wf",
        default_cluster_name=C,
        default_compute_resources_set={"queue": Q, "num_cores": 1},
        workflow_attributes={"test_attribute": "test"}
    )
    wf.add_tasks(tasks)
    wf.run(configure_logging=True)


def create_usage_data_wf(num_tasks: int) -> None:
    """
    Use the task_generator_wf.py script to create a workflow with fake resource usage data.
    
    After workflow runs, UPDATE the task_instance table (columns: usage_str, wallclock, maxrss, maxpss, cpu).
    """
    wf_script_path = Path(__file__).parent.parent.parent / "tests/worker_node/task_generator_wf.py"

    # Create a connection to the database
    db_path = "/tmp/tests.sqlite"
    db_engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=db_engine)

    # Get the max of the task_instance ids
    try:
        with Session() as session:
            sql_select_query = "SELECT MAX(id) AS max_id FROM task_instance;"
            max_id_result = session.execute(text(sql_select_query))
            max_id = max_id_result.scalar() or 0
    except Exception as e:
        print(f"Error getting max id from task_instance table: {e}")
        max_id = 0

    # Generate fake data with noise for the tasks
    generated_data = generate_usage_data(num_tasks, max_id)
    print(f"DEGUB: First row of generated data: {generated_data[0]}")

    # Run the command and wait for it to finish
    print("Running subprocess to attempt creating workflow...")
    try:
        result = subprocess.check_output(["python", str(wf_script_path), "1", "--num-tasks", str(num_tasks)])
        # This line will only run after the command above finishes
        print("Workflow completed!")
    except subprocess.CalledProcessError as e:
        print(f"Error running workflow: {e}")
        return

    # Update the task_instance table with fake data
    print("Updating task_instance table with fake data...")
    try:
        with Session() as session:
            for row in generated_data:
                sql_update_query = f"""
                UPDATE task_instance
                SET usage_str = :usage_str,
                    wallclock = :wallclock,
                    maxrss = :maxrss,
                    maxpss = :maxpss,
                    cpu = :cpu
                WHERE id = :id;
                """
                session.execute(text(sql_update_query), row)
            session.commit()
            print("task_instance table updated with fake data!")
    except Exception as e:
        print(f"Error updating task_instance table: {e}")
        return
    
    # Get workflow_run_id from the task_instance table
    try:
        with Session() as session:
            sql_select_query = f"SELECT workflow_run_id FROM task_instance WHERE id = {max_id + 1};"
            wf_run_id_result = session.execute(text(sql_select_query))
            wf_run_id = wf_run_id_result.scalar()
    except Exception as e:
        print(f"Error getting workflow_run_id from task_instance table: {e}")
        return

    # TODO(?): Update relevant tables with task resource usage data? (task_resources table?). But turns out this is insufficient because the viz is actually POST requesting to http://localhost:8070/api/v3/task_template_resource_usage, i.e. at the task_template level. So new question is how to update this? There is no table for task_template_resource_usage or anything explicitly linking task template to requested resources that I can see in the database besides the task_resources table, which seems to share workflow_run_id
    # Update the task_resources table with fake data
    # print("Updating task_resources table with fake data...")
    # try:
    #     with Session() as session:
    #         fake_requested_resources = """{"num_cores": 1,"memory": 1,"runtime": 3600}"""
    #         sql_update_task_resources_query = """
    #         UPDATE task_resources
    #         SET requested_resources = :requested_resources
    #         WHERE id = :wf_run_id
    #         """
    #         session.execute(text(sql_update_task_resources_query), {"requested_resources": fake_requested_resources, "wf_run_id": wf_run_id})
    #         session.commit()
    #         print("task_resources table updated with fake data!")
    # except Exception as e:
    #     print(f"Error updating task_resources table: {e}")
    #     return


def create_wf(total: int, wf_type: str, num_tasks: int = 5):
    created = 0
    # create #total of workflows; if total is 0, create workflows continuously
    while total == 0 or created < total:
        print("Creating workflow")
        created += 1
        this_wf_type = wf_type
        if this_wf_type == "random":
            this_wf_type = random.choice(["simple", "tired"])
        if this_wf_type == "simple":
            create_simple_wf()
        elif this_wf_type == "tired":
            create_tired_wf()
        elif this_wf_type == "usage_data":
            create_usage_data_wf(num_tasks)
        sleep(10)


# Example usage of the function
if __name__ == "__main__":
    args = parse_arguments()

    # Access the arguments
    url = args.server_url
    os.environ["JOBMON__HTTP__SERVICE_URL"] = "http://localhost:8070"
    os.environ["JOBMON__HTTP__ROUTE_PREFIX"] = "/api/v2"
    wfs = args.wf
    wf_type = args.wf_type
    num_tasks = args.num_tasks
    create_wf(wfs, wf_type, num_tasks)
