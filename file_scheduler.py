import schedule
import time
import logging
import argparse
import shutil
import os
import zipfile
import json

logging.basicConfig(
    filename="file_scheduler.log", 
    level=logging.INFO, 
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class Task:
    def __init__(self, task_id, operation, source, destination=None, schedule_time=None):
        self.task_id = task_id
        self.operation = operation
        self.source = source
        self.destination = destination
        self.schedule_time = schedule_time

    def __repr__(self):
        return f"<Task id={self.task_id}, op={self.operation}, src={self.source}, dst={self.destination}, sched={self.schedule_time}>"

class FileScheduler:
    def __init__(self):
        self.tasks = []
        self.next_id = 1
        self.load_tasks() 

    def save_tasks(self): 
        data = {
            "next_id": self.next_id,
            "tasks": [{"task_id": t.task_id, "operation": t.operation, "source": t.source, "destination": t.destination, "schedule_time": t.schedule_time} for t in self.tasks]
        }
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_tasks(self): 
        if os.path.exists("tasks.json"):
            try:
                with open("tasks.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.next_id = data.get("next_id", 1)
                    for t_data in data.get("tasks", []):
                        task = Task(t_data["task_id"], t_data["operation"], t_data["source"], t_data.get("destination"), t_data.get("schedule_time"))
                        self.tasks.append(task)
                        if task.schedule_time:
                            parts = task.schedule_time.split(':')
                            time_str = f"{parts[1]}:{parts[2]}"
                            if "daily" in task.schedule_time:
                                schedule.every().day.at(time_str).do(self.run_task, task)
                            elif "weekly" in task.schedule_time:
                                schedule.every().monday.at(time_str).do(self.run_task, task)
            except Exception:
                pass 

    def add_task(self, operation, source, destination, schedule_time):
        task = Task(self.next_id, operation, source, destination, schedule_time)
        self.tasks.append(task)
        self.next_id += 1

        if schedule_time:
            parts = schedule_time.split(':')
            time_str = f"{parts[1]}:{parts[2]}"
            if "daily" in schedule_time:
                schedule.every().day.at(time_str).do(self.run_task, task)
            elif "weekly" in schedule_time:
                schedule.every().monday.at(time_str).do(self.run_task, task)
                
        self.save_tasks()  
        print(f"Задача добавлена: {task}")

    def remove_task(self, task_id):
        task_to_remove = next((t for t in self.tasks if t.task_id == task_id), None)
        if task_to_remove:
            self.tasks.remove(task_to_remove)
            self.save_tasks() 
            print(f"Задача с ID {task_id} удалена из списка.")
        else:
            print(f"Задача с ID {task_id} не найдена.")

    def run_task(self, task):
        if task not in self.tasks:
            return
        try:
            if task.operation == 'copy':
                shutil.copy2(task.source, task.destination)
            elif task.operation == 'move':
                shutil.move(task.source, task.destination)
            elif task.operation == 'delete':
                if os.path.isfile(task.source):
                    os.remove(task.source)
                elif os.path.isdir(task.source):
                    shutil.rmtree(task.source)
            elif task.operation == 'archive':
                with zipfile.ZipFile(task.destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    if os.path.isfile(task.source):
                        zipf.write(task.source, os.path.basename(task.source))
                    else:
                        for root, dirs, files in os.walk(task.source):
                            for file in files:
                                file_path = os.path.join(root, file)
                                zipf.write(file_path, os.path.relpath(file_path, task.source))
            else:
                raise ValueError("Неизвестная операция")
            self.log_task(task, "Success")
        except Exception as e:
            self.log_task(task, f"Failed - {str(e)}")

    def log_task(self, task, status):
        logging.info(f"Task ID {task.task_id}: {task.operation} on {task.source} - Status: {status}")

    def start(self):
        print("Шедулер запущен. Нажмите Ctrl+C для остановки.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("Шедулер остановлен.")

def main():
    scheduler = FileScheduler()
    parser = argparse.ArgumentParser(description="Файловый шедулер (Задание 1)")
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

    parser_add = subparsers.add_parser("add", help="Добавить задачу")
    parser_add.add_argument("--op", required=True, choices=['copy', 'move', 'delete', 'archive'], help="Операция")
    parser_add.add_argument("--src", required=True, help="Исходный файл или папка")
    parser_add.add_argument("--dst", help="Путь назначения")
    parser_add.add_argument("--sched", required=True, help="Расписание (например, daily:15:30)")

    subparsers.add_parser("view", help="Просмотр задач")

    parser_del = subparsers.add_parser("delete", help="Удалить задачу")
    parser_del.add_argument("--id", required=True, type=int, help="ID задачи")

    subparsers.add_parser("start", help="Запустить шедулер")

    args = parser.parse_args()

    if args.command == "add":
        if args.op != 'delete' and not args.dst:
            print("Ошибка: для операций copy, move и archive нужно указать --dst")
            return
        scheduler.add_task(args.op, args.src, args.dst, args.sched)
    elif args.command == "view":
        print("Список задач:")
        if not scheduler.tasks:
            print("  (список пуст)")
        for task in scheduler.tasks:
            print(f"  {task}")
    elif args.command == "delete":
        scheduler.remove_task(args.id)
    elif args.command == "start":
        scheduler.start()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()