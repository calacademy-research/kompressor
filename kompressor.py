import os
import pwd
import subprocess
import threading
import time
import argparse
import chardet
import magic

MAX_THREADS = 6


def is_binary(filepath):
    with open(filepath, 'rb') as f:
        content = f.read(1024)
    return b'\x00' in content

#def is_binary(filepath):
#    mime_type= magic.from_file(filepath, mime=True)
#    return mime_type == 'application/octet-stream'

#def is_binary(filepath):
#    cmd = ['file', '-b', '--mime-encoding', filepath]
#    output = subprocess.check_output(cmd).decode('utf-8').strip()
#    if output == 'binary':
#        return True
#    else:
#        return False

#def is_ascii(filepath):
#    print(",", end='', flush=True)
#    try:
#        output = subprocess.check_output(["file", "--mime-encoding", filepath]).decode("utf-8")
#        return output.startswith("ASCII")
#    except subprocess.CalledProcessError:
#        return False


#def detect_encoding(filepath):
#    print(",", end='', flush=True)
#    with open(filepath, 'rb') as f:
#        detector = chardet.UniversalDetector()
#        for line in f.readlines():
#            detector.feed(line)
#            if detector.done:
#                break
#        detector.close()
#        return detector.result['encoding']

def compress_file(filepath, pigz_threads):
    try:
        username = pwd.getpwuid(os.stat(filepath).st_uid).pw_name
        cmd = ['sudo', '-u', username, 'pigz',  '-p', str(pigz_threads), filepath]
#        print(f"Compressing {filepath} with: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        print(f",", end='', flush=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to compress {filepath}: {e}")

import os
import subprocess
import glob
import time


def explore_dir(dir_path, num_threads, num_simultaneous, min_age, min_size, exclude_dirs):
    considered = 0
    rejected = 0
    dots_printed = False
    for root, dirs, files in os.walk(dir_path):
        # Exclude directories starting with dot, containing "conda", or "R"
#        dirs[:] = [d for d in dirs if not any(exclude in os.path.join(root, d) for exclude in exclude_dirs) and not d.startswith('.')]
#        dirs[:] = [d for d in dirs if not d.startswith('.') and 'conda' not in d and d != 'R']
        dirs[:] = [d for d in dirs if not d.startswith('.') and 'conda' not in d and not any(exclude in os.path.join(root, d) for exclude in exclude_dirs)]
        for filename in files:
            filepath = os.path.join(root, filename)
            if os.path.islink(filepath) or is_binary(filepath):
                rejected += 1
                continue
            statinfo = os.stat(filepath)
            age_in_days = (time.time() - statinfo.st_mtime) / 86400.0 #86400 seconds = 1 day
            if age_in_days >= min_age and statinfo.st_size >= min_size*1024 and not is_binary(filepath):
                if dots_printed:
                    print('')
                print(f"Found large ascii file: {filepath}")
                t = threading.Thread(target=compress_file, args=(filepath, num_threads))
                t.start()
                while threading.active_count() > num_simultaneous:
                    time.sleep(0.1)
                dots_printed = False
            else:
                rejected += 1
                dots_printed = True
            considered += 1
            if considered % 30 == 0:
                print('.', end='', flush=True)
                dots_printed = True
    if dots_printed:
        print('')
    print(f"Considered {considered} files, rejected {rejected} files")




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find large ASCII files and compress them using pigz in parallel.')
    parser.add_argument('-t', '--threads', type=int, default=4, help='Number of pigz threads to use (default: 4)')
    parser.add_argument('-s', '--simultaneous', type=int, default=6, help='Maximum number of simultaneous pigz processes (default: 6)')
    parser.add_argument('-a', '--age', type=int, default=30, help='Minimum age of files to consider (in days, default: 30)')
    parser.add_argument('-m', '--size', type=int, default=1, help='Minimum size of files to consider (in MB, default: 1)')
    parser.add_argument('-d', '--dir', type=str, default='/home', help='Directory to start search (default: /home)')
    parser.add_argument('-e', '--exclude', nargs='+', default=['R'], help='Directories to exclude (default: [])')
    args = parser.parse_args()
    
    min_size_bytes = args.size * 1024 * 1024
    explore_dir(args.dir, args.threads, args.simultaneous, args.age, min_size_bytes, args.exclude)


