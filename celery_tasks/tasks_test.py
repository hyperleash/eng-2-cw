from tasks import add, run_merizo, run_pdb_centremass, run_pdb_watercontact
from celery import group
import argparse
import os

parser = argparse.ArgumentParser(description='Process PDB files.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-d','--directory_path', type=str, help='Path to the directory containing PDB files')
args = parser.parse_args()

result = add.delay(4, 5)  # Submit the task to the queue
print(result.get())  # Wait for the result and print it (should output 9)



pdb_files = [os.path.join(args.directory_path, file) for file in os.listdir(args.directory_path) if file.endswith('.pdb')]
print(pdb_files)

merizo_job = group(run_merizo.s(file_path) for file_path in pdb_files)
merizo_results = merizo_job.apply_async()

paths = merizo_results.get()
print(paths)

domain_file_paths = [path for result in paths for path in result] 
# directory_path = args.directory_path 

# result = run_merizo.delay(args.directory_path)
# domain_file_paths = result.get() # Submit the task to the queue
# print(domain_file_paths) 


# Assuming merizo_results contains lists of domain files produced by each task
centermass_tasks = [run_pdb_centremass.s(path) for path in domain_file_paths]
watercontact_tasks = [run_pdb_watercontact.s(path) for path in domain_file_paths]

centermass_job = group(centermass_tasks) 

centermass_result = centermass_job.apply_async()
print(centermass_result.get())


watercontact_job = group(watercontact_tasks)
watercontact_result = watercontact_job.apply_async()
print(watercontact_result.get())