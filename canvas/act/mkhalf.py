import json
p=json.load(open('ws/project.icproj.json'))
d=[x for x in p['documents'] if x['name']=='adc_half'][0]
clr=[{"kind":"delete","target":{"kind":"annotation","id":a['id']}} for a in d['annotations'] if a.get('kind')=='net-label']
clr+=[{"kind":"delete","target":{"kind":"route","id":r['id']}} for r in d['routes']]
pt=dict(vin="cell-pin-533e4e92ca66e5b3",vs="cell-pin-d454259fd72d244d",clk="cell-pin-46ee0f53ea810614",vref="cell-pin-40e590d9ee67d41d",vbn="cell-pin-2558347b7880f130",rst="cell-pin-12b903c174a91434",q0="cell-pin-383ec0ea91c67798",q1="cell-pin-8a9ee235dc4f0fb2",q2="cell-pin-1b3c0f783c7138e0",q3="cell-pin-05cae4016f5b1f96",q4="cell-pin-5e4062de3c6aae1e",q5="cell-pin-a2f4dde24abf9b88",q6="cell-pin-5edd568c734083da",mon="cell-pin-b9a6922a341a66fd",vdd="cell-pin-055aa167c34d93d4",gnd="cell-pin-308c4181ceb3e502")
M=[];W=[];Lb=[]
def mv(i,x,y,r=0):
    M.append({"kind":"set-orientation","target":{"kind":"instance","id":i},"rotation":r,"mirror":"none"}); M.append({"kind":"move","target":{"kind":"instance","id":i},"position":{"x":x,"y":y}})
P=lambda i,q:{"kind":"pin","instance":{"kind":"instance","id":i},"pin":q}
pp=lambda n:P(pt[n],"P")
def cn(a,b,via=None):
    x={"kind":"connect","from":a,"to":b}
    if via: x["via"]=[{"x":u,"y":v} for u,v in via]
    W.append(x)
def lab(i,q,x,y,t,lx,ly):
    W.append({"kind":"connect","from":P(i,q),"to":{"kind":"point","x":x,"y":y}})
    Lb.append({"kind":"add-label","target":P(i,q),"text":t,"position":{"x":lx,"y":ly}})
mv("XLOOP",200,300); mv("XVCO",400,300)
D=[300+80*(i-3) for i in range(7)]
lane=[500,520,540,None,540,520,500]
FA,FB,XX=640,780,900
for i in range(7):
    mv(f"XFA{i}",FA,D[i]+10); mv(f"XFB{i}",FB,D[i]+20); mv(f"XX{i}",XX,D[i]+10); mv(pt[f"q{i}"],1000,D[i]-30,180)
mv("XMON",FA,0); mv(pt["mon"],FA+80,0,180)
mv(pt["vin"],40,240); mv(pt["vref"],40,170); mv(pt["vbn"],40,150); mv(pt["rst"],40,130)
mv(pt["vdd"],260,110,90); mv(pt["gnd"],290,470,270); mv(pt["vs"],420,470,270); mv(pt["clk"],FA-80,D[6]+20)
cn(P("XLOOP","vctrl"),P("XVCO","vin")); cn(pp("vin"),P("XLOOP","vin"))
cn(pp("vref"),P("XLOOP","vref"),[(140,170)]); cn(pp("vbn"),P("XLOOP","vbn"),[(180,150)]); cn(pp("rst"),P("XLOOP","rst"),[(220,130)])
cn(P("XLOOP","vdd"),P("XVCO","vdd"),[(260,160),(400,160)]); cn(pp("vdd"),P("XLOOP","vdd"))
cn(P("XLOOP","gnd"),P("XVCO","gnd"),[(200,440),(380,440)]); cn(pp("gnd"),P("XVCO","gnd"),[(290,440),(380,440)])
cn(P("XVCO","vs"),pp("vs"))
for i in range(7): lab("XLOOP",f"b{i}",90,260+20*i,f"b{i}",85,264+20*i)
for i in range(7):
    py=240+20*i
    if i==3: cn(P("XVCO","ph3"),P("XFA3","D"))
    else: cn(P("XVCO",f"ph{i}"),P(f"XFA{i}","D"),[(lane[i],py),(lane[i],D[i])])
cn(P("XMON","A"),P("XVCO","ph0"),[(500,0),(500,240)]); cn(P("XMON","X"),pp("mon"))
for i in range(7):
    d=D[i]
    cn(P(f"XFA{i}","Q"),P(f"XFB{i}","D"))
    cn(P(f"XFA{i}","Q"),P(f"XX{i}","A"),[(690,d+10),(690,d-30),(XX-50,d-30),(XX-50,d)])
    cn(pp(f"q{i}"),P(f"XX{i}","A"),[(XX-50,d-30),(XX-50,d)])
    cn(P(f"XFB{i}","Q"),P(f"XX{i}","B"))
    lab(f"XX{i}","X",XX+60,d+10,f"b{i}",XX+65,d+14)
    if i!=6: lab(f"XFA{i}","CLK",FA-60,d+20,"clk",FA-60,d+16)
    lab(f"XFB{i}","CLK",FB-60,d+30,"clk",FB-60,d+46)
cn(pp("clk"),P("XFA6","CLK"))
for n,a in (("hc",clr),("hm",M),("hw",W),("hl",Lb)): json.dump({"actions":a},open(f"act/{n}.json","w"))
