from config._loader import data_dir, load

globals().update(load("settings"))

# Fixed path on the data volume.
logs_folder_path = f"{data_dir()}/logs/"
