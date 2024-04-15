from tasks import add, run_prediction

result = add.delay(4, 5)  # Submit the task to the queue
print(result.get())  # Wait for the result and print it (should output 9)

result = run_prediction.delay('/home/ec2-user/data/shared/AF-A0A0A0MRZ7-F1-model_v4.pdb')
print(result.get())  # Submit the task to the queue