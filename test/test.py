import os
import requests

from qubell.api.testing import *
from qubell.api.tools import retry
from testtools import skip


def eventually(*exceptions):
    """
    Method decorator, that waits when something inside eventually happens
    Note: 'sum([delay*backoff**i for i in range(tries)])' ~= 580 seconds ~= 10 minutes
    :param exceptions: same as except parameter, if not specified, valid return indicated success
    :return:
    """
    return retry(tries=50, delay=0.5, backoff=1.1, retry_exception=exceptions)

def check_site(instance):
    # Check we have 2 hosts up
    @eventually(AssertionError, KeyError)
    def eventually_assert():
        assert len(instance.returnValues['endpoints.demosite'])
    eventually_assert()

    # Check site still alive
    url = instance.returnValues['endpoints.demosite']
    resp = requests.get(url)
    assert resp.status_code == 200

@environment({
    "default": {},
    "AmazonEC2_CentOS_63": {
        "policies": [{
            "action": "provisionVms",
            "parameter": "imageId",
            "value": "us-east-1/ami-bf5021d6"
        }, {
            "action": "provisionVms",
            "parameter": "vmIdentity",
            "value": "root"
        }]
  },
    "AmazonEC2_Ubuntu_1204": {
        "policies": [{
            "action": "provisionVms",
            "parameter": "imageId",
            "value": "us-east-1/ami-967edcff"
        }, {
            "action": "provisionVms",
            "parameter": "vmIdentity",
            "value": "ubuntu"
        }]
  },
    "AmazonEC2_Ubuntu_1004": {
        "policies": [{
            "action": "provisionVms",
            "parameter": "imageId",
            "value": "us-east-1/ami-9f3906f6"
        }, {
            "action": "provisionVms",
            "parameter": "vmIdentity",
            "value": "ubuntu"
        }]
  }
})
class BroadleafTestCase(BaseComponentTestCase):
    name = "broadleaf-starter-kit"
    meta = os.path.realpath(os.path.join(os.path.dirname(__file__), '../meta.yml')) 
    destroy_interval = int(os.environ.get('DESTROY_INTERVAL', 1000*60*60*2))
    apps = [{
        "name": name,
        "settings": {"destroyInterval": destroy_interval},
        "file": os.path.realpath(os.path.join(os.path.dirname(__file__), '../%s.yml' % name))
   }]

    @classmethod
    def timeout(cls):
        return 240

    @instance(byApplication=name)
    @values({"lb-host": "host"})
    def test_host(self, instance, host):
	resp = requests.get("http://" + host, verify=False)

        assert resp.status_code == 200

    @instance(byApplication=name)
    @values({"db-port": "port", "db-host": "host"})
    def test_db_port(self, instance, host, port):
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))

        assert result == 0
    
    @instance(byApplication=name)
    def test_solr_search(self, instance):
         hosts = instance.returnValues['endpoints.solr-url']
         
         for host in hosts:
	     resp = requests.get(host + "/select/?q=*:*", verify=False)
             assert resp.status_code == 200

    @instance(byApplication=name)
    def test_broadleaf_up(self, instance):
        check_site(instance)

    @instance(byApplication=name)
    def test_scaling(self, instance):
        assert len(instance.returnValues['endpoints.app']) == 1
        params = {'input.app-quantity': '2'}
        instance.reconfigure(parameters=params)
        assert instance.ready(timeout=45)

        check_site(instance)
        # Check we have 2 hosts up
        @eventually(AssertionError, KeyError)
        def eventually_assert():
            assert len(instance.returnValues['endpoints.app']) == 2
        eventually_assert()

