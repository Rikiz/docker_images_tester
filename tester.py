import subprocess
import os
import re


def sanitize_name(image: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", image)


def test_image(image: str, logs_dir: str) -> dict:
    safe_name = sanitize_name(image)
    image_logs_dir = os.path.join(logs_dir, safe_name)
    os.makedirs(image_logs_dir, exist_ok=True)
    results = {}

    step1_2_cmd = (
        f"cd /home "
        f"&& mkdir -p /logs/{safe_name} "
        f"&& sed -i 's/mvn /mvn -o /g' run.sh test-run.sh fix-run.sh "
        f"&& bash run.sh &>/logs/{safe_name}/run.log; "
        f"echo $? > /logs/{safe_name}/run.rc; "
        f"bash test-run.sh &>/logs/{safe_name}/test-run.log; "
        f"echo $? > /logs/{safe_name}/test-run.rc"
    )
    docker_cmd_1 = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{logs_dir}:/logs",
        image,
        "bash",
        "-c",
        step1_2_cmd,
    ]

    try:
        subprocess.run(docker_cmd_1, timeout=600)
    except subprocess.TimeoutExpired:
        results["run"] = {"returncode": -1, "status": "timeout"}
        results["test-run"] = {"returncode": -1, "status": "skipped"}
        results["fix-run"] = {"returncode": -1, "status": "skipped"}
        return {"image": image, "results": results}
    except Exception as e:
        results["run"] = {"returncode": -1, "status": f"error: {e}"}
        results["test-run"] = {"returncode": -1, "status": "skipped"}
        results["fix-run"] = {"returncode": -1, "status": "skipped"}
        return {"image": image, "results": results}

    for script in ["run", "test-run"]:
        rc_file = os.path.join(image_logs_dir, f"{script}.rc")
        try:
            with open(rc_file) as f:
                rc = int(f.read().strip())
            os.remove(rc_file)
        except (FileNotFoundError, ValueError):
            rc = -1
        results[script] = {"returncode": rc, "status": "pass" if rc == 0 else "fail"}

    step3_cmd = (
        f"cd /home "
        f"&& mkdir -p /logs/{safe_name} "
        f"&& sed -i 's/mvn /mvn -o /g' run.sh test-run.sh fix-run.sh "
        f"&& bash fix-run.sh &>/logs/{safe_name}/fix-run.log; "
        f"echo $? > /logs/{safe_name}/fix-run.rc"
    )
    docker_cmd_2 = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{logs_dir}:/logs",
        image,
        "bash",
        "-c",
        step3_cmd,
    ]

    try:
        subprocess.run(docker_cmd_2, timeout=600)
    except subprocess.TimeoutExpired:
        results["fix-run"] = {"returncode": -1, "status": "timeout"}
        return {"image": image, "results": results}
    except Exception as e:
        results["fix-run"] = {"returncode": -1, "status": f"error: {e}"}
        return {"image": image, "results": results}

    rc_file = os.path.join(image_logs_dir, "fix-run.rc")
    try:
        with open(rc_file) as f:
            rc = int(f.read().strip())
        os.remove(rc_file)
    except (FileNotFoundError, ValueError):
        rc = -1
    results["fix-run"] = {"returncode": rc, "status": "pass" if rc == 0 else "fail"}

    return {"image": image, "results": results}
