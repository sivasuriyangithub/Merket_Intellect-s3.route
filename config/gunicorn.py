import multiprocessing

workers = min(
    multiprocessing.cpu_count() * 2 + 1, 20
)  # k8s request should expect ~110mb per process
timeout = 180
graceful_timeout = 500
