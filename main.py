import os
import sys
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed

from tester import test_image, sanitize_name


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def print_summary(all_results: list[dict]):
    print(f"\n{'Image':<30} {'run.sh':<12} {'test-run.sh':<14} {'fix-run.sh':<12}")
    print("-" * 68)
    for r in all_results:
        img = r["image"]
        res = r["results"]
        run_s = res.get("run", {}).get("status", "N/A")
        test_s = res.get("test-run", {}).get("status", "N/A")
        fix_s = res.get("fix-run", {}).get("status", "N/A")
        print(f"{img:<30} {run_s:<12} {test_s:<14} {fix_s:<12}")


def main():
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "config.yaml"
    )
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)
    images = config.get("images", [])
    concurrency = config.get("concurrency", 4)

    if not images:
        print("No images configured in config.yaml")
        sys.exit(1)

    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    print(f"Testing {len(images)} image(s) with concurrency={concurrency}")
    print(f"Logs directory: {logs_dir}\n")

    all_results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(test_image, img, logs_dir): img for img in images}
        for future in as_completed(futures):
            img = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                print(f"[DONE] {img}")
            except Exception as e:
                all_results.append({"image": img, "results": {}})
                print(f"[FAIL] {img}: {e}")

    print_summary(all_results)


if __name__ == "__main__":
    main()
