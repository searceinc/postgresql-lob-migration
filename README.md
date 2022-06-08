# Postgres-lobject

This multithreading utility can be used to migrate PostgreSQL lobject data.

## Prerequisites

* python3.9 

## Setup environment 

The commands below will create a virtual environment, update pip to the latest version, and install the packages required to use this utility.

```
bin\setup.sh setup
```

## Based on your project requirement change in config/app.setting.json file

```
"MinPoolSize": Min connection pool.  
"PoolSize": Max connection pool.  
"WorkerPool": Node Worker Threads.
```

The database node is where you'll make changes to the source and destination connection strings.

## Run application

Run application with below command 

```
python3.9 app.py
```

