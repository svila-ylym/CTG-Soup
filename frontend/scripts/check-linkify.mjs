import assert from 'node:assert/strict'
import { linkifyText } from '../src/utils/linkifyText.ts'

function links(text) {
  return linkifyText(text).filter((segment) => segment.type === 'link')
}

function link(text) {
  assert.deepEqual(links(text).map((segment) => segment.href), [text])
}

link('https://example.com')
link('http://localhost:8080/a?b=1#top')
link('https://例子.测试/路径')
assert.deepEqual(links('查看 https://example.com/path。'), [
  { type: 'link', text: 'https://example.com/path', href: 'https://example.com/path' },
])
assert.deepEqual(links('(https://example.com/path)'), [
  { type: 'link', text: 'https://example.com/path', href: 'https://example.com/path' },
])
assert.deepEqual(links('https://example.com/(path)'), [
  { type: 'link', text: 'https://example.com/(path)', href: 'https://example.com/(path)' },
])
assert.equal(links('http://').length, 0)
assert.equal(links('http://.').length, 0)
assert.equal(links('ftp://example.com').length, 0)
assert.equal(links('wordhttp://example.com').length, 0)
assert.equal(links('javascript:http://example.com').length, 0)
assert.equal(links('https://').length, 0)
assert.equal(links('http://example.com)abc').length, 0)
assert.equal(links('https://example.com/<script>').length, 1)
assert.equal(links('访问https://example.com/path').length, 1)
assert.equal(links('https://example.com/path,').at(0)?.href, 'https://example.com/path')
assert.deepEqual(
  links('先看 https://one.example/a，再看 http://two.example:8080/b#c').map((segment) => segment.href),
  ['https://one.example/a', 'http://two.example:8080/b#c'],
)

console.log('linkify checks passed')
