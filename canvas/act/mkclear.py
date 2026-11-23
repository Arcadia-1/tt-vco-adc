import json,sys
doc=sys.argv[1]; p=json.load(open('ws/project.icproj.json'))
def find(o):
    if isinstance(o,dict):
        if o.get('id')==doc and ('routes' in o or 'annotations' in o or 'content' in o): return o
        for v in o.values():
            r=find(v)
            if r: return r
    elif isinstance(o,list):
        for v in o:
            r=find(v)
            if r: return r
d=find(p); print(list(d.keys()),file=sys.stderr)
c=d.get('content',d)
A=[]
def walk(o):
    if isinstance(o,dict):
        if o.get('kind')=='net-label': A.append({"kind":"delete","target":{"kind":"annotation","id":o['id']}})
        for v in o.values(): walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(c)
routes=[]
def wr(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='routes' and isinstance(v,list): routes.extend(r['id'] for r in v if isinstance(r,dict) and 'id' in r)
            wr(v)
    elif isinstance(o,list):
        for v in o: wr(v)
wr(c)
A+= [{"kind":"delete","target":{"kind":"route","id":r}} for r in routes]
print(len(A),file=sys.stderr)
json.dump({"actions":A},open(sys.argv[2],'w'))
