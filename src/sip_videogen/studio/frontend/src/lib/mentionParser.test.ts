//Unit tests for mention parser
import{describe,it,expect}from'vitest'
import{parseMentions,resolveMentions,isValidTriggerPosition,getCurrentMention}from'./mentionParser'
import type{ProductEntry}from'./bridge'
describe('parseMentions',()=>{
it('parses single product mention',()=>{
const result=parseMentions('@product:morning-complete')
expect(result).toEqual([{type:'product',slug:'morning-complete'}])})
it('parses single template mention',()=>{
const result=parseMentions('@template:hero-banner')
expect(result).toEqual([{type:'template',slug:'hero-banner'}])})
it('parses multiple mentions',()=>{
const result=parseMentions('Use @product:foo and @template:bar together')
expect(result).toHaveLength(2)
expect(result).toContainEqual({type:'product',slug:'foo'})
expect(result).toContainEqual({type:'template',slug:'bar'})})
it('handles trailing punctuation',()=>{
const result=parseMentions('@product:foo, and @template:bar.')
expect(result).toEqual([{type:'product',slug:'foo'},{type:'template',slug:'bar'}])})
it('deduplicates same mention',()=>{
const result=parseMentions('@product:foo and @product:foo again')
expect(result).toHaveLength(1)})
it('is case-insensitive',()=>{
const result=parseMentions('@PRODUCT:FOO and @Product:Bar')
expect(result).toEqual([{type:'product',slug:'foo'},{type:'product',slug:'bar'}])})
it('ignores email addresses',()=>{
const result=parseMentions('Contact user@domain.com for info')
expect(result).toEqual([])})
it('handles multiline input',()=>{
const result=parseMentions('Line 1 @product:a\nLine 2 @template:b')
expect(result).toHaveLength(2)})
it('returns empty for no mentions',()=>{
const result=parseMentions('Just some regular text')
expect(result).toEqual([])})})
describe('resolveMentions',()=>{
const products:ProductEntry[]=[
{slug:'morning-complete',name:'Morning Complete',description:'',primary_image:'',attribute_count:0,created_at:'',updated_at:''},
{slug:'night-cream',name:'Night Cream',description:'',primary_image:'',attribute_count:0,created_at:'',updated_at:''}]
const templates=[
{slug:'hero-banner',name:'Hero Banner',description:'',primary_image:'',default_strict:true,created_at:'',updated_at:''},
{slug:'product-shot',name:'Product Shot',description:'',primary_image:'',default_strict:false,created_at:'',updated_at:''}]
it('resolves valid product mention',()=>{
const result=resolveMentions('@product:morning-complete',products,templates)
expect(result.products).toEqual(['morning-complete'])
expect(result.templates).toEqual([])})
it('resolves valid template mention with default_strict',()=>{
const result=resolveMentions('@template:hero-banner',products,templates)
expect(result.products).toEqual([])
expect(result.templates).toEqual([{template_slug:'hero-banner',strict:true}])})
it('uses template default_strict value',()=>{
const result=resolveMentions('@template:product-shot',products,templates)
expect(result.templates[0].strict).toBe(false)})
it('ignores invalid slugs',()=>{
const result=resolveMentions('@product:nonexistent',products,templates)
expect(result.products).toEqual([])
expect(result.templates).toEqual([])})
it('resolves mixed mentions',()=>{
const result=resolveMentions('@product:night-cream and @template:hero-banner',products,templates)
expect(result.products).toEqual(['night-cream'])
expect(result.templates).toEqual([{template_slug:'hero-banner',strict:true}])})})
describe('isValidTriggerPosition',()=>{
it('returns false at position 0',()=>{
expect(isValidTriggerPosition('@hello',0)).toBe(false)})
it('returns true for @ at start',()=>{
expect(isValidTriggerPosition('@',1)).toBe(true)})
it('returns true after space',()=>{
expect(isValidTriggerPosition('hello @',7)).toBe(true)})
it('returns false in middle of word',()=>{
expect(isValidTriggerPosition('email@domain',6)).toBe(false)})
it('returns true after punctuation',()=>{
expect(isValidTriggerPosition('test,@',6)).toBe(true)})})
describe('getCurrentMention',()=>{
it('returns null when no @',()=>{
expect(getCurrentMention('hello world',5)).toBeNull()})
it('returns all type for just @',()=>{
const result=getCurrentMention('@',1)
expect(result).toEqual({start:0,query:'',type:'all'})})
it('returns all type for @partial',()=>{
const result=getCurrentMention('@pro',4)
expect(result).toEqual({start:0,query:'pro',type:'all'})})
it('returns product type for @product:',()=>{
const result=getCurrentMention('@product:morn',13)
expect(result).toEqual({start:0,query:'morn',type:'product'})})
it('returns template type for @template:',()=>{
const result=getCurrentMention('@template:hero',14)
expect(result).toEqual({start:0,query:'hero',type:'template'})})
it('handles mention after text',()=>{
const result=getCurrentMention('Use @product:foo',16)
expect(result).toEqual({start:4,query:'foo',type:'product'})})
it('returns null for invalid trigger position',()=>{
expect(getCurrentMention('email@domain',12)).toBeNull()})})
