"""Secondary Bonsai assignment search penalizing the busiest CZ wire.

Objective = adjacent-CX count proxy +4*max(per-wire adjacent-CX incidences).
This is a search proxy, NOT compiled CZ depth. Majorana pairs stay intact.
"""
import math
import numpy as np
from cuprate_2d_fermionic_mapping import pair_model


def balance(mapping,cfg,seed=27,proposals=15000):
    costs=mapping.cost_matrices()
    loads=np.zeros((2,mapping.n,mapping.n,mapping.n))
    for p in range(mapping.n):
        for q in range(p+1,mapping.n):
            for kind,paulis in enumerate((mapping.hopping_nodes(p,q),mapping.onsite_nodes(p,q))):
                profile=np.zeros(mapping.n)
                for pauli in paulis:
                    gates,_=mapping.parity_plan(pauli.support)
                    for a,b in gates: profile[a]+=2; profile[b]+=2
                loads[kind,p,q]=loads[kind,q,p]=profile
    h,u=pair_model(cfg)
    terms=[(p,q,0) for (p,q),c in h.items() if c]+[(p,q,1) for (p,q),c in u.items() if c]
    incidents=[[] for _ in range(mapping.n)]
    for k,(p,q,_) in enumerate(terms): incidents[p].append(k); incidents[q].append(k)
    assignment=mapping.assignment.copy()
    def subset(ids):
        total=0.; load=np.zeros(mapping.n)
        for k in ids:
            p,q,kind=terms[k]; a,b=assignment[p],assignment[q]
            total+=costs[kind][a,b]; load+=loads[kind,a,b]
        return total,load
    total,load=subset(range(len(terms)))
    score=total+4*max(load); initial=score; best=score
    best_assignment=assignment.copy(); trace=[]; rng=np.random.default_rng(seed)
    for k in range(proposals):
        p,q=rng.choice(mapping.n,2,replace=False); touched=set(incidents[p]+incidents[q])
        old_cost,old_load=subset(touched)
        assignment[p],assignment[q]=assignment[q],assignment[p]
        new_cost,new_load=subset(touched)
        proposed_load=load+new_load-old_load
        proposed_total=total+new_cost-old_cost
        proposed_score=proposed_total+4*max(proposed_load)
        delta=proposed_score-score
        temperature=10*(.02/10)**(k/max(1,proposals-1))
        if delta<=0 or rng.random()<math.exp(-min(700,delta/temperature)):
            total,load,score=proposed_total,proposed_load,proposed_score
            if score<best: best=score; best_assignment=assignment.copy()
        else: assignment[p],assignment[q]=assignment[q],assignment[p]
        if (k+1)%1000==0: trace.append({'proposal':k+1,'score':score,'best':best})
    assignment=best_assignment
    total,load=subset(range(len(terms)))
    if abs(total+4*max(load)-best)>1e-7: raise AssertionError('Load objective update drift')
    mapping.set_assignment(assignment)
    return {'seed':seed,'proposals':proposals,'initial_score':float(initial),'best_score':float(best),
        'native_count_proxy':float(total),'peak_wire_CX_proxy':float(max(load)),
        'wire_loads':load.tolist(),'assignment':assignment,'trace':trace,
        'not_actual_compiled_depth':True}
