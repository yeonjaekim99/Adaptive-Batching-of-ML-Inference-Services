#!/usr/bin/python3
import os
import sys
import threading
import time, subprocess
import string

proper_rate=[]

b_num = 6   # Number of batch sizes #
b_factor = 10   # Increase the batch size by multiple of n #
r_num = 7 # Number of request rates #

batch_info = open('./results/batch_info.txt','w')

for i in range(b_num):
    # Set the batch size #
    if i == 0:
        batch = 1
    else:
        batch = i*b_factor


    # Modify the batch size of the model config file #
    temp = "\"5s/.*/  preferred_batch_size: [ "+str(batch)+", "+str(batch)+" ]/g\"" # Modify from '5' to nth line according to the config file #
    os.system("sed -i %s /home/yeonjae/KYJ/models/vgg19/vgg19/config.pbtxt"%temp) # Set the config file path appropriately #

    time.sleep(10) # Time for config file to be modified #

    # Execute server #
    server_command = ['docker', 'run', '--gpus','\"device=3\"', '--rm', '-p8000:8000', '-p8001:8001', '-p8002:8002', '--hostname=server', '--name=yj_server2', '-v', '/home/yeonjae/KYJ/models:/models', 'nvcr.io/nvidia/tritonserver:21.06-py3', 'tritonserver', '--model-repository=/models/vgg19', '--allow-gpu-metrics=false']
    server = subprocess.Popen(server_command)

    time.sleep(15) # Time for the server to be executed #

    # Execute client #
    filename = "/results/batch"+str(batch)+".txt"
    client_command = ['docker', 'run', '--rm', '--name=yj_client2', '-v','/home/yeonjae/KYJ/results:/results', '--net=host', 'nvcr.io/nvidia/tritonserver:21.06-py3-sdk', 'perf_analyzer', '-m' ,'vgg19', '--measurement-mode=count_windows', '-b',str(batch), '-f', filename, '--measurement-request-count',str(batch*10)]
    client = subprocess.Popen(client_command)

    # Wait for the client to shut down #
    client.wait()

    # Calculate the appropriate request rate #
    filename = "./results/batch"+str(batch)+".txt"
    f = open(filename, 'r')
    line = f.readline()
    line = f.readline()
    line_num = line.split(',')
    compute_time = int(line_num[5]) + int(line_num[6]) + int(line_num[7])
    proper_rate.append((batch*1000000)//compute_time)
    batch_info.write("Batch %d ComputeTime(s) %f ProperRate %d\n"%(batch,compute_time/1000000,proper_rate[i]))
    print("\n### batch %d proper request rate : %d ###\n"%(batch,proper_rate[i]))
    f.close()

    # Experiment is conducted around the appropriate rate #
    for j in range(r_num):
        rate = (j + 1) * 50  + round(proper_rate[i],-1) - (r_num//2+1) * 50
        if rate <= 0:
            continue
        filename = "/results/batch"+str(batch)+"rate"+str(rate)+".txt"
        client_command = ['docker', 'run', '--rm', '--name=yj_client2', '-v','/home/yeonjae/KYJ/results:/results', '--net=host', 'nvcr.io/nvidia/tritonserver:21.06-py3-sdk', 'perf_analyzer', '-m' ,'vgg19', '--measurement-mode=count_windows','--request-distribution=poisson','--max-threads=32' ,'-a' ,'-b','1', '-f', filename,'--request-rate-range',str(rate), '--measurement-request-count',str(rate*10)]
        client = subprocess.Popen(client_command)
        # Wait for the client to shut down #
        client.wait()

    # Shut down the server and wait until it is shut down #
    server.terminate()
    server.wait()

batch_info.close()
