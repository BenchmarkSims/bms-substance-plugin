import os

import substance_painter.ui
import substance_painter.export
import substance_painter.project
import substance_painter.textureset
import substance_painter.event

import subprocess
import concurrent
import threading
from concurrent.futures import ThreadPoolExecutor as Pool

from PySide2 import QtWidgets

plugin_widgets = []


def export_dds_textures(export_result):
    print(f"export_dds_textures"
          f"{export_result}")
    total_files_to_process = 0

    if export_result.status != substance_painter.export.ExportStatus.Success:
        return

    albedo_files = []
    armw_files = []
    emission_files = []
    normal_files = []

    for stack, files in export_result.textures.items():
        for exported_filename in files:
            if os.path.splitext(exported_filename)[0].endswith("_Albedo"):
                albedo_files.append(os.path.abspath(exported_filename))
            elif os.path.splitext(exported_filename)[0].endswith("_ARMW"):
                armw_files.append(os.path.abspath(exported_filename))
            elif os.path.splitext(exported_filename)[0].endswith("_Emission"):
                emission_files.append(os.path.abspath(exported_filename))
            elif os.path.splitext(exported_filename)[0].endswith("_Normal"):
                normal_files.append(os.path.abspath(exported_filename))

            else:
                print(f"Warning: unknown file pattern {exported_filename}, will not be converted to DDS")

    texconv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "texconv.exe")
    if not os.path.exists(texconv_path):
        print(f"Error: texconv.exe not found in {texconv_path}")
        return

    total_files_to_process = len(albedo_files) + len(armw_files) + len(emission_files) + len(normal_files)
    files_completed = 0
    pool = Pool(max_workers=2)
    futures = []
    semaphore = threading.Semaphore()

    progress_widget = QtWidgets.QProgressDialog("Converting to DDS...", "Cancel", 0, total_files_to_process)
    plugin_widgets.append(progress_widget)
    progress_widget.setValue(0)
    progress_widget.setCancelButton(None)
    progress_widget.show()

    def _worker_callback(future):
        nonlocal total_files_to_process
        nonlocal files_completed
        nonlocal progress_widget
        nonlocal semaphore

        semaphore.acquire()
        files_completed += 1
        progress_widget.setValue(files_completed)
        print(f"{files_completed} / {total_files_to_process} files exported")

        if future.exception() is not None:
            print("got exception: %s" % future.exception())

        if files_completed == total_files_to_process:
            print("Export completed")
            progress_widget.close()

        semaphore.release()

    for albedo_file in albedo_files:
        print(f"processing albedo file: {albedo_file}: \n"
              f'"{texconv_path}" -nologo -y -f BC7_UNORM_SRGB -srgb "{albedo_file}"')
        output_directory = os.path.dirname(albedo_file)

        future = pool.submit(subprocess.call,
                             f'"{texconv_path}" -nologo -y -f BC7_UNORM_SRGB -srgb -o "{output_directory}" "{albedo_file}"',
                             shell=True)
        future.add_done_callback(_worker_callback)
        futures.append(future)
        # texconv.exe -nologo -y -f BC7_UNORM_SRGB -srgb PreviewSphere_Sphere_Albedo.tif

    for armw_file in armw_files:
        print(f"processing armw file: {armw_file}")
        output_directory = os.path.dirname(albedo_file)

        future = pool.submit(subprocess.call,
                             f'"{texconv_path}" -nologo -y -f BC7_UNORM -o "{output_directory}" "{armw_file}"',
                             shell=True)
        future.add_done_callback(_worker_callback)
        futures.append(future)
        # texconv.exe -nologo -y -f BC7_UNORM PreviewSphere_Sphere_ARMW.tif

    for emission_file in emission_files:
        print(f"processing emission file: {emission_file}")
        output_directory = os.path.dirname(albedo_file)

        future = pool.submit(subprocess.call,
                             f'"{texconv_path}" -nologo -y -f BC7_UNORM -o "{output_directory}" "{emission_file}"',
                             shell=True)
        future.add_done_callback(_worker_callback)
        futures.append(future)
        # texconv.exe -nologo -y -f BC7_UNORM PreviewSphere_Sphere_ARMW.tif

    for normal_file in normal_files:
        print(f"processing normal_file file: {normal_file}")
        output_directory = os.path.dirname(albedo_file)

        future = pool.submit(subprocess.call,
                             f'"{texconv_path}" -nologo -y -f BC5_UNORM -o "{output_directory}" "{normal_file}"',
                             shell=True)
        future.add_done_callback(_worker_callback)
        futures.append(future)
        # texconv.exe -nologo -y -f BC5_UNORM PreviewSphere_Sphere_Normal.tif


def start_plugin():
    substance_painter.event.DISPATCHER.connect(substance_painter.event.ExportTexturesEnded, export_dds_textures)


def close_plugin():
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)

    plugin_widgets.clear()


if __name__ == "__main__":
    start_plugin()


