#!/usr/bin/python3
import os
import sys
import threading
import time, subprocess
import string

b_num = 20   # Number of batch sizes #
b_factor = 5   # Increase the batch size by multiple of n #

compute_info = open('./results/resnet50.txt','a')

for i in range(b_num):
    # Set the batch size #
    if i == 0:
        batch = 1
    else:
        batch = i*b_factor


    # Modify the batch size of the model config file #
    temp = "\"5s/.*/  preferred_batch_size: [ "+str(batch)+", "+str(batch)+" ]/g\"" # Modify from '5' to nth line according to the config file #
    os.system("sed -i %s /home/yeonjae/KYJ/models/resnet50/r50v2/config.pbtxt"%temp) # Set the config file path appropriately #

    time.sleep(10) # Time for config file to be modified #

    # Execute server #
    server_command = ['docker', 'run', '--gpus','\"device=3\"', '--rm', '-p8000:8000', '-p8001:8001', '-p8002:8002', '--hostname=server', '--name=yj_server2', '-v', '/home/yeonjae/KYJ/models:/models', 'nvcr.io/nvidia/tritonserver:21.07-py3', 'tritonserver', '--model-repository=/models/resnet50', '--allow-gpu-metrics=false']
    server = subprocess.Popen(server_command)

    time.sleep(20) # Time for the server to be executed #

    # Execute client #
    filename = "/results/resnet50_batch"+str(batch)+".txt"
    client_command = ['docker', 'run', '--rm', '--name=yj_client2', '-v','/home/yeonjae/KYJ/results:/results', '--net=host', 'nvcr.io/nvidia/tritonserver:21.07-py3-sdk', 'perf_analyzer', '-m' ,'r50v2', '--measurement-mode=count_windows', '-b',str(batch), '-f', filename, '--measurement-request-count',str(batch*10)]
    client = subprocess.Popen(client_command)

    # Wait for the client to shut down #
    client.wait()

    # Calculate the compute time #
    filename = "./results/resnet50_batch"+str(batch)+".txt"
    f = open(filename, 'r')
    line = f.readline()
    line = f.readline()
    line_num = line.split(',')
    compute_time = int(line_num[5]) + int(line_num[6]) + int(line_num[7])
    compute_info.write("%d %d\n"%(batch,compute_time))
    print("\n### batch %d compute time : %d ###\n"%(batch,compute_time))
    f.close()

    # Shut down the server and wait until it is shut down #
    server.terminate()
    server.wait()

compute_info.close()
