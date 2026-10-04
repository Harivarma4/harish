"""Regenerate the GitLab pack outputs from plan.json.

Usage: python3 pack_gen.py <pack-dir>
Writes <pack-dir>/issues_import.csv and <pack-dir>/backlog_full.md from <pack-dir>/plan.json.
Verified 4 Oct 2026 to reproduce the attached pack byte for byte. plan.json is written with
json.dumps(indent=1, ensure_ascii=False).
"""
import json,csv,io,re
def csvdesc(i):
    s=i['description']+"\n\n/label "+" ".join('~"%s"'%l for l in i['labels'])+"\n/milestone %\""+i['milestone']+"\""
    if i.get('estimate'): s+="\n/estimate "+i['estimate']
    return s
def render_csv(plan):
    out=io.StringIO(newline='')
    w=csv.writer(out)
    w.writerow(['title','description','due_date','milestone'])
    for i in plan['issues']:
        w.writerow([i['title'],csvdesc(i),i.get('due_date') or '',i['milestone']])
    return out.getvalue()
def bsec(i):
    s="### %s\n\nLabels: %s · Milestone: %s · Estimate: %s"%(i['title'],", ".join(i['labels']),i['milestone'],i.get('estimate') or 'TBD')
    return s+"\n\n"+re.sub(r'^## ','#### ',i['description'],flags=re.M)
def gen(p):
    out=["# Q4 2026 Data Platform Roadmap – full GitLab backlog\n\n"]
    re_=p['roadmap_epic']
    out.append("# %s\n\n%s\n\n\n\n"%(re_["title"],re_["description"]))
    byf={}
    for i in p['issues']: byf.setdefault(i['feature'],[]).append(i)
    feats={}
    for f in p['features']: feats.setdefault(f['epic'],[]).append(f)
    def feat(f):
        s="## Feature %s · %s\n\n%s\n\n\n"%(f['id'],f['title'],f['note'])
        for i in byf.get(f['id'],[]): s+=bsec(i)+"\n\n\n"
        return s
    for f in feats.get('E0',[]): out.append(feat(f))
    for e in p['epics']:
        out.append("# Epic %s · %s\n\n%s\n\n\n"%(e['id'],e['title'],e['description']))
        for f in feats.get(e['id'],[]): out.append(feat(f))
    return ''.join(out).rstrip('\n')+'\n'


if __name__ == "__main__":
    import json, os, sys
    d = sys.argv[1]
    p = json.load(open(os.path.join(d, "plan.json")))
    csv_text = render_csv(p)
    md_text = gen(p)
    with open(os.path.join(d, "issues_import.csv"), "w", newline="") as f:
        f.write(csv_text)
    with open(os.path.join(d, "backlog_full.md"), "w") as f:
        f.write(md_text)
    print(len(p["issues"]), "issues")
