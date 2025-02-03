from kombu import Exchange, Queue

from config import Config

broker_uri = Config.TASK_BROKER_URI
result_backend = Config.TASK_RESULT_BACKEND
task_ignore_result = True

task_queues = (Queue("default", Exchange("default"), routing_key="default"),)
task_default_queue = "default"
task_default_routing_key = "default"
task_routes = {
    "src.services.tasks.tasks.notification": {
        "queue": "high",
        "routing_key": "high",
    },
    "src.services.tasks.tasks.perco.get_*": {
        "queue": "high",
        "routing_key": "high",
    },
    "src.services.tasks.tasks.perco": {
        "queue": "default",
        "routing_key": "default",
    },
    "src.services.tasks.tasks.db": {
        "queue": "default",
        "routing_key": "default",
    },
}

imports = ("src.services.task.tasks.db",)
