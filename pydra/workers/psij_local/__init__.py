import typing as ty
import cloudpickle as cp
import logging
import attrs
import psij
from pydra.engine.job import Job
from pydra.workers import base
from pydra.utils.general import SCRIPTS_DIR

logger = logging.getLogger("pydra.worker")

if ty.TYPE_CHECKING:
    from pydra.engine.result import Result


@attrs.define
class Worker(base.Worker):
    """A worker to execute tasks using PSI/J."""

    subtype = "local"

    def make_spec(self, cmd=None, arg=None):
        """
        Create a PSI/J job specification.

        Parameters
        ----------
        cmd : str, optional
            Executable command. Defaults to None.
        arg : list, optional
            List of arguments. Defaults to None.

        Returns
        -------
        psij.JobDef
            PSI/J job specification.
        """
        spec = psij.JobSpec()
        spec.executable = cmd
        spec.arguments = arg

        return spec

    def make_job(self, spec, attributes):
        """
        Create a PSI/J job.

        Parameters
        ----------
        task : psij.JobDef
            PSI/J job specification.
        attributes : any
            Job attributes.

        Returns
        -------
        psij.Job
            PSI/J job.
        """
        job = psij.Job()
        job.spec = spec
        return job

    async def run(
        self,
        job: Job[base.TaskType],
        rerun: bool = False,
    ) -> "Result":
        """
        Run a job (coroutine wrapper).

        Raises
        ------
        Exception
            If stderr is not empty.

        Returns
        -------
        None
        """
        jex = psij.JobExecutor.get_instance(self.subtype)

        cache_root = job.cache_root
        file_path = cache_root / "runnable_function.pkl"
        with open(file_path, "wb") as file:
            cp.dump(job.run, file)
        func_path = SCRIPTS_DIR / "run_pickled.py"
        spec = self.make_spec("python", [func_path, file_path])

        if rerun:
            spec.arguments.append("--rerun")

        spec.stdout_path = cache_root / "demo.stdout"
        spec.stderr_path = cache_root / "demo.stderr"

        psij_job = self.make_job(spec, None)
        jex.submit(psij_job)
        psij_job.wait()

        if spec.stderr_path.stat().st_size > 0:
            with open(spec.stderr_path, "r") as stderr_file:
                stderr_contents = stderr_file.read()
            raise Exception(
                f"stderr_path '{spec.stderr_path}' is not empty. Contents:\n{stderr_contents}"
            )

        return job.result()

    def close(self):
        """Finalize the internal pool of tasks."""
        pass
