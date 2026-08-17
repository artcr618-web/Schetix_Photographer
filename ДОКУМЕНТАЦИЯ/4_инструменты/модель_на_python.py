# -*- coding: utf-8 -*-
"""Независимая реализация формулы calc() из web/calc.html — для проверки тождеств."""
FIX,THR,CRED,CAP,M15,M20,MO,Q = 57390,300000,3000,321818,.01,.03,12,4
WD,VAC,SICK,EFF,DW = 247,20,8,7,5
ND=WD-VAC-SICK; NT=ND*EFF; NW=ND/DW

CAT={
 'Form001':('life',[166999/3,130999/5,36990/5,9355/5,12978/3,6990/2,6990/2,27962/7,3000/5,5000/7]),
 'Form002':('life',[180000/5,55000/5,30000/5,5000/5,3500/7,4000/3,15999/5,3500/5,29999/5]),
 'Form003':('per',[2000*12,250*12]),
 'Form004':('life',[6900/3]*5),
 'Form013':('life',[35000/7,30000/7]),
 'Form007':('per',[0*12,150*12]),
 'Form010':('per',[1500*1,6000*1,15000*12,0,0,0,0]),
}
def sumF(f): return sum(CAT[f][1])

def calc(regime='npd5', income_month=110216, S=1.0, K=3.0, cl=1.0, promo_per_day=2.0,
         acc_mode='self', acc_per_quarter=3, acc_cost_month=10000,
         ws_mode='home', home_rent=40000, home_util=7000, home_area=50, cab_area=6,
         office_rent=15000, office_util=7000,
         edu_life=7, edu_sum=80000, edu_months=4,
         site_mode='hired', site_cost=70000, site_life=7, site_hours=80,
         acq_rate=2.7, acq_share=100, fund_on=False, fund_pct=15,
         disc_on=False, disc_pct=15, fm_on=False, fm_pct=10, tax_off=False,
         current_rate=6000):
    promo=promo_per_day*ND
    self_acc=(acc_mode=='self')
    accT=acc_per_quarter*Q if self_acc else 0
    idle=ND*(8-EFF)
    side=promo+accT; gross=NT-side
    fmT=gross*(fm_pct/100) if fm_on else 0
    pool=gross-fmT
    M=1+K
    pt=S*M+cl; py=pool/pt if pt>0 else 0; sh=py*S; post=sh*K; core=sh+post; clT=py*cl
    wsShare=cab_area/home_area if home_area>0 else 0
    wsY=(home_rent+home_util)*wsShare*MO if ws_mode=='home' else (office_rent+office_util)*MO
    eduOpp=edu_months*income_month
    eduY=(edu_sum+eduOpp)/edu_life if edu_life>0 else 0
    siteSelf=(site_mode=='self')
    siteY=0 if siteSelf else (site_cost/site_life if site_life>0 else 0)
    sdiv=(site_hours/(site_life*NT)) if (siteSelf and site_life>0) else 0
    equip=sumF('Form001')+sumF('Form002')+sumF('Form004')
    amort=equip+sumF('Form013')+eduY+siteY
    accM=0 if self_acc else acc_cost_month*MO
    vari=sumF('Form003')+sumF('Form010')+sumF('Form007')+accM+wsY
    C=amort+vari
    Ny=income_month*MO
    a=(acq_rate/100)*(acq_share/100)
    fundP=(fund_pct/100) if fund_on else 0
    discP=(disc_pct/100) if disc_on else 0
    rg=regime
    RT={'npd5':.05,'npd4':.04,'npd6':.06,'usn6':.06,'usn15':.15,'ausn8':.08,'ausn20':.20}[rg]
    if tax_off: RT=0
    D=1-a-sdiv-fundP-discP
    if tax_off: R=(Ny+C)/D
    elif rg.startswith('npd'): R=(Ny+C)/(D-RT)
    elif rg=='usn6': R=max((Ny+C+FIX-CRED)/(D-.01),(Ny+C)/(D-.06))
    elif rg=='usn15':
        TB=Ny/(1-.15); R=(TB+FIX-CRED+.01*TB+C)/D
    elif rg=='ausn8': R=(Ny+C)/(D-.08)
    else:
        TB2=Ny/(1-.20); R=(TB2+C)/D
    def taxOf(Rx):
        if tax_off: return 0
        t=0;c2=0
        if rg.startswith('npd'): t=Rx*RT
        elif rg=='usn6':
            c2=FIX+min(max(0,Rx-THR)*.01,CAP); t=max(0,Rx*.06-c2)
        elif rg=='usn15':
            B=Ny/(1-.15); c2=FIX+min(max(0,B-THR)*.01,CAP); t=max(B*.15,Rx*M15)
        elif rg=='ausn8': t=Rx*.08
        else:
            B2=Ny/(1-.20); t=max(B2*.20,Rx*M20)
        return t+c2
    taxAll=taxOf(R); aq=R*a
    fundY=R*fundP; discY=R*discP
    mt=0 if tax_off else (RT if rg.startswith('npd') else .01 if rg=='usn6' else M15 if rg=='usn15' else RT if rg=='ausn8' else M20)
    Rb=(C+(FIX if (not tax_off and rg.startswith('usn')) else 0))/(D-mt)
    return dict(R=R,C=C,Ny=Ny,taxAll=taxAll,aq=aq,sh=sh,pool=pool,pt=pt,py=py,post=post,core=core,
                clT=clT,side=side,fmT=fmT,idle=idle,promo=promo,accT=accT,Rb=Rb,taxB=taxOf(Rb),
                aqB=Rb*a,fundY=fundY,discY=discY,sdiv=sdiv,D=D,rate=R/sh if sh else 0,
                amort=amort,vari=vari,wsY=wsY,eduY=eduY,siteY=siteY,a=a,regime=rg)
