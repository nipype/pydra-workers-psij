from pydra.workers import psij_local


class Worker(psij_local.Worker):
    """A worker to execute tasks using PSI/J using SLURM."""

    subtype = "slurm"
