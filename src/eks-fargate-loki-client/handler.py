import logging
import logging_loki
import os
import sys
import asyncio
from kubernetes import client, config,watch
import threading
import ctypes
import typing
import concurrent.futures

# required environment variables.
namespaces = os.environ.get('NAMESPACE')
loki_url = os.environ.get('LOKI_URL')

if not namespaces:
    sys.stderr.write('Environment Variable NAMESPACE is required.\n')
if not loki_url:
    sys.stderr.write('Environment Variable LOKI_URL is required.\n')

namespaces = namespaces.split(',')

ignore_apps = os.environ.get('IGNORE_APPS')
# giving a default if nothing is given - log-exporter ? this one
if(not ignore_apps):
    ignore_apps = 'log-exporter'

ignore_apps = ignore_apps.split(',')
sys.stderr.write('Ignoring logs from apps -')
[sys.stderr.write('%s ' %i) for i in ignore_apps]
sys.stderr.write('\n')

ignore_containers = os.environ.get('IGNORE_CONTAINERS')

if(not ignore_containers):
    ignore_containers = 'metrics'
ignore_containers = ignore_containers.split(',')
sys.stderr.write('Ignoring logs from containers -')
[sys.stderr.write('%s ' %i) for i in ignore_containers]
sys.stderr.write('\n')

try:
    config.load_kube_config()  # may be in development mode
except TypeError:
    config.load_incluster_config()

v1 = client.CoreV1Api()

class PodLogThread(threading.Thread):
    def __init__(self, name:str,app:str,pod:str,container:str,namespace:str): 
        threading.Thread.__init__(self) 
        self.name = name
        self.pod =pod
        self.namespace = namespace
        self.container = container
        self.app = app
        
        handler = None
        try:
            handler = logging_loki.LokiHandler(url="%s/loki/api/v1/push" % os.environ['LOKI_URL'], tags={"app": "%s-%s" %(self.namespace,self.app)}, version="1",)
            def handleError(er):
                return
            handler.handleError = handleError
        except: #noqa
            sys.stderr.write('Error in creating LokiHandler %s-%s-%s\n' %(self.namespace,self.app,self.container))
        self.logger = logging.getLogger("%s-%s" %(self.namespace,self.app))
        if(not handler):
            sys.stderr.write('Handler not added for %s-%s-%s\n' %(self.namespace,self.app,self.container))
        else:
            self.logger.addHandler(handler)
        
        
    def terminate(self): 
        self._running = False
    def run(self):
        v1 = client.CoreV1Api()
        w = watch.Watch()
        pod_stream = None
        try:
            pod_stream = w.stream(v1.read_namespaced_pod_log, name=self.pod, namespace=self.namespace,container=self.container)
        except:
            message = "%s %s %s" % (sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            sys.stderr.write('Unable to create Pod Stream %s-%s-%s\n' %(self.namespace,self.app,self.container) )
            sys.stderr.write('%s \n' %(message))
        if(pod_stream):
            try:
                for e in pod_stream:
                    try:
                        self.logger.error(e, extra={"tags": {"app": self.app,"namespace":self.namespace,"container":self.container}},)
                    except:
                        sys.stderr.write('Logging error %s-%s-%s\n' %(self.namespace,self.app,self.container) )
            except:
                message = "%s %s %s" % (sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
                sys.stderr.write('Pod Stream Iteration error %s-%s-%s\n' %(self.namespace,self.app,self.container) )
                sys.stderr.write('%s \n' %(message))
                self._running = False

 
    def get_id(self): 
        # returns id of the respective thread 
        if hasattr(self, '_thread_id'): 
            return self._thread_id 
        for id, thread in threading._active.items(): 
            if thread is self: 
                return id
   
    def raise_exception(self): 
        thread_id = self.get_id() 
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 
              ctypes.py_object(SystemExit)) 
        if res > 1: 
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0) 
            sys.stderr.write('Exception raise failure\n')

def pods(namespace:str):
    w = watch.Watch()
    for count,pod in enumerate(w.stream(v1.list_namespaced_pod,namespace=namespace)):
        pod_name=pod.get('object').metadata.name
        app = pod.get('object').metadata.labels.get('app')
        event= pod.get('type')
        sys.stderr.write('%d-%s-%s-%s-%s' %(count,namespace,pod_name,app,event))
        containers = list(map(lambda x: x.name, pod.get('object').spec.containers))
        # ignore the containers which are not needed
        containers = list(filter(lambda x: x not in ignore_containers ,containers))
        if(event == 'ADDED'):
            sys.stderr.write('add %s in namespace %s \n' % (pod_name,namespace))
            if(len(list(filter(lambda x: pod_name.startswith(x),ignore_apps))) == 0 ):
                for container in containers:
                    at = PodLogThread(name='%s-%s-%s'%(namespace,pod_name,container),app=app,pod=pod_name,namespace=namespace,container=container)
                    at.start()
                    sys.stderr.write('added %s %s %s\n'%(namespace,pod_name,container))
        elif(event == 'DELETED'):
            sys.stderr.write('Deleted %s-%s' %(namespace,pod_name))
            sys.stderr.write('Watching the following only now \n')
            [sys.stderr.write('%s ' % th.name) for th in threading.enumerate()]
        


async def tail_logs(executor,namespaces):
    loop = asyncio.get_event_loop()
    blocking_tasks = [loop.run_in_executor(executor,pods,namespace) for namespace in namespaces]
    await asyncio.wait(blocking_tasks)

ioloop = asyncio.get_event_loop()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(namespaces),)
try:
    ioloop.run_until_complete(tail_logs(executor,namespaces))
finally:
    ioloop.close()





