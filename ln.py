"""
LND

Usage:
  ln.py forwardtx [--aggr] [--loop]

Options:
  -h --help     Show this screen.
  --aggr    asdf

"""

import os, grpc, time, datetime, json
import config
import libs.rpc_pb2 as ln
import libs.rpc_pb2_grpc as lnrpc
import threading
import time
from docopt import docopt

def metadata_callback(context, callback):
    callback([("macaroon", macaroon)], None)

os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"
macaroon = open(config.macaroon_path, "rb").read().hex()
cert = open(config.cert_path, "rb").read()
cert_creds = grpc.ssl_channel_credentials(cert)
auth_creds = grpc.metadata_call_credentials(metadata_callback)
combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
grpc_options = [
    ("grpc.max_receive_message_length", config.grpc_max_length),
    ("grpc.max_send_message_length", config.grpc_max_length),
]
channel = grpc.secure_channel(
    config.lnd_grpc_server, combined_creds, options=grpc_options
)
stub = lnrpc.LightningStub(channel)


node_info = stub.GetInfo(ln.GetInfoRequest())
node_info_detail = stub.GetNodeInfo(
        ln.NodeInfoRequest(pub_key=node_info.identity_pubkey)
    )
node_pub_key = node_info_detail.node.pub_key
def getAlias(ChanInfo):
    if ChanInfo.node1_pub == node_pub_key:
        node_pub =  ChanInfo.node2_pub
    else:
        node_pub =  ChanInfo.node1_pub

    node_info = stub.GetNodeInfo(
            ln.NodeInfoRequest(pub_key=node_pub))
    alias = node_info.node.alias
    return alias,ChanInfo.channel_id

def list(aggr=False):
    events_response = stub.ForwardingHistory(
        ln.ForwardingHistoryRequest(
            start_time=0,
            end_time=int(time.time()),
            index_offset=0,
            num_max_events=100000,
        )
    )
    events = []
    events_aggr = []

    for index,event in enumerate(events_response.forwarding_events):
        chan_info_in = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=event.chan_id_in))
        chan_info_out = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=event.chan_id_out))
        node_in,chan_in_id = getAlias(chan_info_in)
        node_out,chan_out_id = getAlias(chan_info_out)
        #print(event)
        events.append(
            {
                'index': index,
                'time':event.timestamp,
                'chan_in':chan_in_id,
                'node_in':node_in,
                'chan_out':chan_out_id,
                'node_out':node_out,
                'amt':event.amt_out
            }
        )

        events_filter = [x for x in events_aggr if x['chan_in'] == chan_in_id and x['chan_out'] == chan_out_id]

        if len(events_filter) > 0:
            index = events_aggr.index(events_filter[0])
            events_aggr[index]["count"] = events_aggr[index]["count"] + 1
            events_aggr[index]["amt"] = events_aggr[index]["amt"] + event.amt_out
        else:
            events_aggr.append(
                {
                    'count':1,
                    'chan_in':chan_in_id,
                    'node_in':node_in,
                    'chan_out':chan_out_id,
                    'node_out':node_out,
                    'amt':event.amt_out
                }
            )

    if aggr:
        for e in events_aggr:
            print(str(e['count']) + ' ' + str(e['chan_in']) + ' ' + e['node_in'] + ' --> [ ] --> ' + str(e['chan_out']) + ' ' + e['node_out'] + ' ' + str(e['amt']))
    else:
        for e in events:
            print(str(e['index'] + 1) + ' ' + datetime.datetime.fromtimestamp(e['time']).strftime("%d-%m-%Y %H:%M") + ': ' + str(e['chan_in']) + ' '  + e['node_in'] + \
            ' --> [ ] --> ' + str(e['chan_out']) + ' '  + e['node_out'] + ' amount: ' + str(e['amt']))

     #events_aggr = [(x,y,z,a) for x,y,z,a in groupby(events, itemgetter(2,3))]

    #print(events_aggr)
def listloop():
    while True:
        list()
        print('----------------------------------------------------------------------------------------------------------------------')
        time.sleep(60 * 10)

def main(args):
    if args['--loop']:
        thread = threading.Thread(target=listloop, name="fwtx")
        thread.start()
    else:
        if args["forwardtx"]:
            list(args['--aggr'])

if __name__ == '__main__':
    # print(docopt(__doc__))
    main(docopt(__doc__))
