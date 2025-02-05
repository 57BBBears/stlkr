from kombu import Exchange, Queue

task_ignore_result = True

task_queues = (Queue("default", Exchange("default"), routing_key="default"),)
task_default_queue = "default"
task_default_routing_key = "default"
task_routes = {
    "src.services.task.tasks.parser": {
        "queue": "default",
        "routing_key": "default",
    },
}

imports = ("src.services.task.tasks.parser",)
