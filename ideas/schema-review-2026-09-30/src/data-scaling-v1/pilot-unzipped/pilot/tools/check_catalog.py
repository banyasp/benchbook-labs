import yaml,re
cat=yaml.safe_load(open('/home/claude/data-scaling/pilot/catalog-F.yaml'))['catalog']
ocr=open('/home/claude/data-scaling/pilot/raw/sead4_ocr.txt').read()
ocr=re.sub(r'=== \S+\n','',ocr); ocr=re.sub(r'\n\d+\nUNCLASSIFIED\n','\n',ocr); ocr=ocr.replace('UNCLASSIFIED','')
norm=lambda s: re.sub(r'\s+',' ',s.replace('’',"'").replace('“','"').replace('”','"')).strip()
O=norm(ocr); bad=0
texts=[q['text'] for q in cat['default']['quotes']]+[cat['concern']['text']]
for sec in ('factors_B','factors_A'):
    for k,v in cat[sec].items(): texts.append(v['text'])
for t in texts:
    if norm(t) not in O: bad+=1; print('MISSING:',t[:90])
print(f'{len(texts)} quotes checked, {bad} not found verbatim')
