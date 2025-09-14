import subprocess
from time import perf_counter

from deployment_builder.keywords import CREATE, DELETE
from deployment_builder.logging_config import get_logger


class Kind:
    def __init__(self, name=None):
        self.log = get_logger("kind")

    def create(self, name):
        self.log.info(f"deleting cluster {name}")
        self._process(name, CREATE)

    def delete(self, name):
        self.log.info(f"deleting cluster {name}")
        self._process(name, DELETE)

    def _process(self, name, action):
        start = perf_counter()
        cmd = ["kind", action, "cluster", "--name", name]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False  # Don't raise exception on non-zero exit
        )
        success = result.returncode == 0

        # Log output if requested (debug level) or if there was an error
        if result.stdout:
            self.log.debug(f"Kind stdout: {result.stdout}")
        if result.stderr:
            self.log.debug(f"Kind stderr: {result.stderr}")

        end = perf_counter()
        if success:
            self.log.info(f"Kind {action} command completed successfully, time taken: {end - start}")
        else:
            self.log.error(
                f"Kind {action} command failed with return code {result.returncode}, time taken: {end - start}"
            )
