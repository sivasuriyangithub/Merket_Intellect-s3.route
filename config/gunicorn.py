import multiprocessing

workers = min(
    int(multiprocessing.cpu_count() * 1.2), 20
)  # k8s request should expect ~110mb per process
timeout = 180
graceful_timeout = 500
