//Utility functions for file processing and conversion
import{ALLOWED_IMAGE_EXTS,ALLOWED_TEXT_EXTS}from'./constants'
//Get file extension with leading dot
export function getFileExtension(filename:string):string{const parts=filename.split('.');return parts.length>1?'.'+parts.pop()!.toLowerCase():''}
//Check if file extension is an allowed image type
export function isAllowedImageExt(filename:string):boolean{const ext=getFileExtension(filename);return(ALLOWED_IMAGE_EXTS as readonly string[]).includes(ext)}
//Check if file extension is an allowed text type
export function isAllowedTextExt(filename:string):boolean{const ext=getFileExtension(filename);return(ALLOWED_TEXT_EXTS as readonly string[]).includes(ext)}
//Convert a file to data URL (includes mime type prefix)
export function fileToDataUrl(file:File):Promise<string>{return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result as string);reader.onerror=()=>reject(new Error(`Failed to read file: ${file.name}`));reader.readAsDataURL(file)})}
//Convert a file to base64 string (without mime type prefix)
export async function fileToBase64(file:File):Promise<string>{const dataUrl=await fileToDataUrl(file);const[,base64]=dataUrl.split(',');return base64||dataUrl}
export interface ProcessedFile{file:File;dataUrl:string;base64:string;type:'image'|'document'}
export interface ProcessFilesResult{processed:ProcessedFile[];rejected:string[]}
//Process uploaded files: validate extensions, read as dataUrl and base64
export async function processUploadedFiles(files:FileList|File[],allowedExts:readonly string[]):Promise<ProcessFilesResult>{
const fileArray=Array.from(files)
const processed:ProcessedFile[]=[]
const rejected:string[]=[]
for(const file of fileArray){
const ext=getFileExtension(file.name)
if(!allowedExts.includes(ext)){rejected.push(file.name);continue}
try{
const dataUrl=await fileToDataUrl(file)
const base64=dataUrl.split(',')[1]||dataUrl
const type=isAllowedImageExt(file.name)?'image':'document'
processed.push({file,dataUrl,base64,type})
}catch{rejected.push(file.name)}}
return{processed,rejected}}
//Process image files only
export function processImageFiles(files:FileList|File[]):Promise<ProcessFilesResult>{return processUploadedFiles(files,ALLOWED_IMAGE_EXTS)}
//Process document files only
export function processDocumentFiles(files:FileList|File[]):Promise<ProcessFilesResult>{return processUploadedFiles(files,ALLOWED_TEXT_EXTS)}
