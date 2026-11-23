import json
port=dict(ua_0="cell-pin-a3844d9dd39261d9",ua_1="cell-pin-65f5a0901929462b",clk="cell-pin-c7ab248d68cb7bdb",rst_n="cell-pin-baf6257d9264c076",
 VDPWR="cell-pin-fb94ab3e03ffdb2d",VGND="cell-pin-eb6398d9c0f42ab3",
 uo_out_0="cell-pin-f292099038d5c814",uo_out_1="cell-pin-5ba4c65a4457e5c6",uo_out_2="cell-pin-cc75e791a01de350",uo_out_3="cell-pin-f39f4c85b4dc44a6",
 uo_out_4="cell-pin-8f41846b01da06f4",uo_out_5="cell-pin-be6ff50f6bc70fde",uo_out_6="cell-pin-b5b3c1b1718e7eac",uo_out_7="cell-pin-c5ff673a6182cec2",
 uio_out_0="cell-pin-4b3e7ee2173c5680",uio_out_1="cell-pin-bc8afa5c668b2afc",uio_out_2="cell-pin-99cd5cfcc7f6494c",uio_out_3="cell-pin-19bb045ae5b1aac0",
 uio_out_4="cell-pin-2011c48efa318b38",uio_out_5="cell-pin-fe00a406d51ff49c",uio_out_6="cell-pin-85964eadbba3f45c",uio_out_7="cell-pin-6dae922bfd162a38")
M=[];W=[]
I=lambda i:{"kind":"instance","id":i}
def mv(i,x,y,r=0,m="none"):
    M.append({"kind":"set-orientation","target":I(i),"rotation":r,"mirror":m}); M.append({"kind":"move","target":I(i),"position":{"x":x,"y":y}})
P=lambda i,p:{"kind":"pin","instance":I(i),"pin":p}
pp=lambda n:P(port[n],"P")
pt=lambda x,y:{"kind":"point","x":x,"y":y}
def cn(a,b,via=None):
    d={"kind":"connect","from":a,"to":b}
    if via: d["via"]=[{"x":x,"y":y} for x,y in via]
    W.append(d)
def wa(x,y,n=None):
    d={"kind":"wire-at","point":{"x":x,"y":y}}
    if n: d["net"]=n
    return d
XC=580
mv("XHP",XC,220); mv("XHN",XC,660,0,"vertical")
qp=["uo_out_6","uo_out_2","uo_out_3","uo_out_5","uo_out_1","uo_out_4","uo_out_0"]
qn=["uio_out_1","uio_out_5","uio_out_4","uio_out_2","uio_out_6","uio_out_3","uio_out_7"]
for i in range(7):
    mv(port[qp[i]],780,150+20*i,180); cn(P("XHP",f"q{i}"),pp(qp[i]))
    mv(port[qn[i]],780,730-20*i,180); cn(P("XHN",f"q{i}"),pp(qn[i]))
mv(port["uo_out_7"],780,290,180); cn(P("XHP","mon"),pp("uo_out_7"))
mv(port["uio_out_0"],780,590,180); cn(P("XHN","mon"),pp("uio_out_0"))
mv(port["ua_0"],XC,80,90); cn(pp("ua_0"),P("XHP","vin"))
mv(port["ua_1"],XC,800,270); cn(pp("ua_1"),P("XHN","vin"))
# straight buses
for n in ("vref","clk","rst","vbn"): cn(P("XHP",n),P("XHN",n))
# resistor array column x=340
mv("RP2_2",340,260); mv("RP1_2",340,320); mv("RN1_2",340,620,180); mv("RN2_2",340,560,180)
cn(P("XHP","vs"),P("RP2_2","1"),[(340,220)]); cn(P("RP2_2","2"),P("RP1_2","1"))
cn(P("XHN","vs"),P("RN1_2","1"),[(340,660)]); cn(P("RN1_2","2"),P("RN2_2","1"))
cn(P("RP1_2","2"),P("RN2_2","2"))
mv(port["VGND"],290,440,0); cn(pp("VGND"),wa(340,440))
# vref leg x=440
mv("Rt_2",440,390); mv("Rbt_2",440,460); mv("XMc_2",400,470,90)
cn(P("Rt_2","2"),P("Rbt_2","1")); cn(P("Rbt_2","2"),wa(340,500),[(440,500)])
cn(P("Rt_2","2"),wa(520,410))
cn(P("XMc_2","G"),wa(440,420),[(400,420)])
for p,x in (("S",380),("D",420)): cn(P("XMc_2",p),wa(x,500))
cn(P("XMc_2","B"),wa(400,500))
mv(port["VDPWR"],440,340,90); cn(pp("VDPWR"),P("Rt_2","1"))
# vbn leg x=680
W.append({"kind":"add-power-rail","start":{"x":680,"y":360},"end":{"x":720,"y":360},"name":"VDPWR"})
W.append({"kind":"add-power-rail","start":{"x":680,"y":500},"end":{"x":740,"y":500},"name":"VGND"})
mv("Rb_2",700,390); mv("XMb_2",710,460,0,"horizontal")
cn(P("Rb_2","1"),wa(700,360)); cn(P("Rb_2","2"),P("XMb_2","D")); cn(P("XMb_2","S"),wa(700,500))
cn(P("XMb_2","G"),wa(700,420),[(730,420)])
cn(P("Rb_2","2"),wa(640,410))
# clk from left, rst from inverter on right
mv(port["clk"],390,540,0); cn(pp("clk"),wa(560,540))
mv("XINV",740,530,180); mv(port["rst_n"],820,530,180); cn(pp("rst_n"),P("XINV","A")); cn(P("XINV","Y"),wa(600,530))
json.dump({"actions":M},open('act/top1.json','w')); json.dump({"actions":W},open('act/top2.json','w'))
