"""Parse an official Council record and its numbered enacted PDF from local files."""
import argparse
import calendar
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin
import pymupdf
from bs4 import BeautifulSoup

def effective_date(text, enacted):
    clauses=re.findall(r'This local law (?:shall )?takes? effect[^.]*\.',text,re.I)
    if len(clauses)!=1: raise ValueError('No unique commencement clause')
    clause=clauses[0]
    if any(word in clause.lower() for word in ('except','provided')):
        raise ValueError('Commencement requires assessment: '+clause)
    if re.search(r'take(?:s)? effect immediately',clause,re.I): return enacted,clause
    m=re.search(r'(\d+) (days?|months?|years?) after (?:it becomes law|this local law becomes law|becoming law)',clause,re.I)
    if m:
        n=int(m[1]); unit=m[2].lower().rstrip('s'); date=dt.date.fromisoformat(enacted)
        if unit=='day': result=date+dt.timedelta(days=n)
        else:
            value=date.year*12+date.month-1+n*(12 if unit=='year' else 1)
            year,month=divmod(value,12);month+=1
            result=dt.date(year,month,min(date.day,calendar.monthrange(year,month)[1]))
        return result.isoformat(),clause
    m=re.search(r'(?:on |effect )([A-Z][a-z]+ \d{1,2},? \d{4})',clause)
    if m: return dt.datetime.strptime(m[1].replace(',',''),'%B %d %Y').date().isoformat(),clause
    raise ValueError('Commencement requires assessment: '+clause)

def parse(record_bytes, pdf_bytes, record_url, pdf_url):
    soup=BeautifulSoup(record_bytes,'html.parser')
    fields={x.get('id').split('_')[-1]:x.get_text(' ',strip=True) for x in soup.select('span[id]')}
    number=fields.get('lblEnactmentNumber2','')
    if not re.fullmatch(r'\d{4}/\d+',number): raise ValueError('No enacted Local Law number')
    links=[urljoin(record_url,a['href']) for a in soup.select('a[href*="View.ashx"]') if re.fullmatch(r'Local Laws?\s+0*'+str(int(number.split('/')[1])),a.get_text(' ',strip=True),re.I)]
    if links!=[pdf_url]: raise ValueError('PDF does not match the numbered enacted attachment')
    enacted=dt.datetime.strptime(fields['lblEnactmentDate2'],'%m/%d/%Y').date().isoformat()
    if not pdf_bytes.startswith(b'%PDF'): raise ValueError('Not an enacted PDF')
    doc=pymupdf.open(stream=pdf_bytes,filetype='pdf')
    if any(page.get_images(full=True) for page in doc): raise ValueError('Image-bearing source requires assessment')
    source='\n'.join(page.get_text(sort=True) for page in doc)
    if len(source.split())<40: raise ValueError('Insufficient native source text')
    text='\n'.join(re.sub(r'[ \t\u00a0]+',' ',line).strip() for line in source.splitlines() if line.strip())+'\n'
    day,clause=effective_date(' '.join(source.split()),enacted)
    year,no=number.split('/');slug=f'nyc-local-law-{year}-{int(no):03d}'
    label=f'New York City Local Law {int(no)} of {year}';title=fields['lblTitle2']
    act={'slug':slug,'short':label,'title':title,'url':record_url,'first_law':slug,'earlier_laws':[],'law_kind':'ordinance','enacted':enacted,
        'versions':[{'from':day,'source_url':pdf_url,'sha256':hashlib.sha256(pdf_bytes).hexdigest(),'in_force_basis':'Enactment date '+enacted+' from the Council record; final instrument states: '+clause,
          'source_images':0,'images_omitted':[],'image_inventory_required':True,'units':{'full-text':{'label':'Full final instrument','kind':'text','text':text}},'credits':{},
          'note':'Full final instrument as enacted, including source drafting headings; not a consolidated Code or Charter version.'}]}
    law={'label':label,'title':title,'kind':'law','law_kind':'ordinance','enacted':enacted,'url':record_url}
    return {'acts':[act],'laws':{slug:law}}

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('record',type=Path);cli.add_argument('pdf',type=Path)
    cli.add_argument('--record-url',required=True);cli.add_argument('--pdf-url',required=True)
    args=cli.parse_args()
    print(json.dumps(parse(args.record.read_bytes(),args.pdf.read_bytes(),args.record_url,args.pdf_url),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
