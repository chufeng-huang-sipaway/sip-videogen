//GenerationSummary - Shows API call summary as compact info
import type {ImageGenerationMetadata} from '@/lib/bridge'
interface Props{metadata:ImageGenerationMetadata;onViewFullDetails?:()=>void}
export function GenerationSummary({metadata,onViewFullDetails}:Props){
const refCount=metadata.reference_images?.length||(metadata.reference_image?1:0)
const genTime=metadata.generation_time_ms?`${(metadata.generation_time_ms/1000).toFixed(1)}s`:null
return(<div className="text-xs space-y-1">
{metadata.model&&<div><span className="text-muted-foreground">Model:</span> {metadata.model}</div>}
{metadata.aspect_ratio&&<div><span className="text-muted-foreground">Aspect ratio:</span> {metadata.aspect_ratio}</div>}
{refCount>0&&<div><span className="text-muted-foreground">Reference images:</span> {refCount}</div>}
{metadata.product_slugs&&metadata.product_slugs.length>0&&(
<div><span className="text-muted-foreground">Products:</span>{' '}{metadata.product_slugs.join(', ')} <span className="text-success">✓</span></div>)}
{genTime&&<div><span className="text-muted-foreground">Generation time:</span> {genTime}</div>}
{metadata.validation_attempts!=null&&metadata.validation_attempts>1&&(
<div><span className="text-muted-foreground">Validation attempts:</span> {metadata.validation_attempts}
{metadata.validation_passed===true&&<span className="text-success ml-1">✓ passed</span>}
{metadata.validation_passed===false&&<span className="text-muted-foreground ml-1">⚠ warnings</span>}</div>)}
{metadata.validation_warning&&(<div className="text-muted-foreground text-xs">⚠ {metadata.validation_warning}</div>)}
{onViewFullDetails&&metadata.api_call_code&&(<button type="button" onClick={onViewFullDetails} className="text-primary hover:underline mt-1">View full API call →</button>)}
</div>)}
