"""Run after creating an EMPTY repository in your own GitHub account."""
import argparse
from pathlib import Path
import re
import subprocess

p=argparse.ArgumentParser()
p.add_argument('url',help='Your actual https://github.com/OWNER/REPOSITORY URL')
a=p.parse_args()
url=a.url.removesuffix('.git').rstrip('/')
if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',url):
    p.error('Use your actual GitHub repository URL, with no credentials or query string.')
root=Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.run(['git',*args],cwd=root,check=True,capture_output=True,text=True).stdout.strip()
if not (root/'.git').exists():
    git('init','-b','main')
existing=git('remote')
if 'origin' in existing.splitlines():
    if git('remote','get-url','origin').removesuffix('.git').rstrip('/') != url:
        raise SystemExit('Origin points to another repository; inspect it before publishing.')
else:
    git('remote','add','origin',url+'.git')
# Ask Git to authenticate through its configured credential manager; never embed a token.
git('push','-u','origin','main')
link=root/'submission/Repository_Link.txt'
link.write_text(url+'\n',encoding='utf-8')
explanation=root/'submission/Phase2_Explanation_200_words.txt'
explanation.write_text(explanation.read_text(encoding='utf-8').replace('[REPOSITORY_URL]',url),encoding='utf-8')
git('add','submission/Repository_Link.txt','submission/Phase2_Explanation_200_words.txt')
if git('status','--porcelain'):
    git('commit','-m','Add verified GitHub repository link for portfolio submission')
    git('push')
print('Published:',url)
print('Submit Repository_Link.txt and paste the 200-word explanation into PebblePad.')
