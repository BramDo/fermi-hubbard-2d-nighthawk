<?php
// Read-only WordPress verification after the scoped publication completed.
// Writes only its receipt file; never republishes, reorders or edits site content.
if (!defined('WP_CLI') || !WP_CLI) { throw new RuntimeException('WP-CLI required'); }
if (rtrim(home_url(), '/') !== 'https://edukaizen.nl') { throw new RuntimeException('Wrong site'); }
$before=json_decode(file_get_contents(__DIR__.'/before_signatures.json'),true,512,JSON_THROW_ON_ERROR);
$receipt=json_decode(file_get_contents(__DIR__.'/publish_receipt.json'),true,512,JSON_THROW_ON_ERROR);
$pkg=json_decode(file_get_contents(__DIR__.'/publish_package.json'),true,512,JSON_THROW_ON_ERROR);
if (count($receipt['pages'])!==10 || count($receipt['menu_items'])!==10 || $receipt['status']!=='IN_PROGRESS') { throw new RuntimeException('Unexpected recovery stage'); }
foreach ($before['posts'] as $id=>$signature) {
    $p=get_post((int)$id,ARRAY_A);
    $now=hash('sha256',wp_json_encode(array_intersect_key($p,array_flip(['ID','post_title','post_content','post_excerpt','post_name','post_parent','post_status','post_type']))));
    if ($now!==$signature) { throw new RuntimeException('Unrelated page/post changed'); }
}
$items=wp_get_nav_menu_items(3); $after=[];
foreach ($items as $m) {
    $after[(string)$m->ID]=['title'=>$m->title,'url'=>$m->url,'parent'=>(int)$m->menu_item_parent,'order'=>(int)$m->menu_order,'object'=>$m->object,'object_id'=>(int)$m->object_id];
}
$shifts=[];
foreach ($before['menu'] as $id=>$old) {
    if (!isset($after[$id])) { throw new RuntimeException('Existing menu item missing'); }
    $now=$after[$id];
    if ($now['order']!==$old['order']) { $shifts[]=['id'=>(int)$id,'title'=>$old['title'],'before'=>$old['order'],'after'=>$now['order'],'stored_menu_order'=>(int)get_post((int)$id)->menu_order]; }
    unset($old['order'],$now['order']);
    if ($old!==$now) { throw new RuntimeException('Existing menu fields changed'); }
}
// WP returns consecutive display positions. Advantage List has stored order 1000;
// its ordinal naturally grows from 88 to 98 when this branch is added before it.
if ($shifts!==[['id'=>452,'title'=>'Advantage List','before'=>88,'after'=>98,'stored_menu_order'=>1000]]) { throw new RuntimeException('Unexpected ordinal shift; inspect rather than mutate'); }
$old_ids=array_keys($before['menu']);
$filtered_ids=array_values(array_filter(array_keys($after),function($id) use($before){ return isset($before['menu'][$id]); }));
if ($old_ids!==$filtered_ids) { throw new RuntimeException('Relative order of existing menu changed'); }
global $wpdb;
foreach ($pkg['pages'] as $entry) {
    $part=(int)$entry['part']; $row=$receipt['pages'][$part]; $p=get_post($row['id']);
    if (!$p || $p->post_status!=='publish' || $p->post_title!==$entry['title'] || $p->post_name!==$entry['slug'] || (int)$p->post_parent!==$row['parent'] || $p->post_content!==$entry['html'] || get_permalink($p)!==$entry['url']) { throw new RuntimeException('Published page mismatch'); }
    if (hash('sha256',$p->post_content)!==$entry['sha256'] || get_post_meta($p->ID,'_nh_series3_owner',true)!=='nighthawk-series3') { throw new RuntimeException('Ownership/checksum mismatch'); }
    $matches=$wpdb->get_col($wpdb->prepare("SELECT ID FROM {$wpdb->posts} WHERE post_type='page' AND post_name=%s AND post_parent=%d",$entry['slug'],$row['parent']));
    if (count($matches)!==1 || (int)$matches[0]!==$row['id']) { throw new RuntimeException('Duplicate/ambiguous page'); }
    $menu=$receipt['menu_items'][$part]; $m=$after[$menu['id']]??null;
    if (!$m || $m['object_id']!==$row['id'] || $m['parent']!==$menu['parent'] || $m['title']!==$entry['menu_label'] || $m['url']!==$entry['url']) { throw new RuntimeException('New navigation mismatch'); }
}
if (count($items)!==count($before['menu'])+10) { throw new RuntimeException('Unexpected menu count'); }
$receipt['unrelated_posts_preserved']=count($before['posts']);
$receipt['existing_menu_items_preserved']=count($before['menu']);
$receipt['existing_menu_fields_and_relative_order_preserved']=true;
$receipt['computed_menu_position_changes']=$shifts;
$receipt['recovery_note']='Publication had completed. Initial strict ordinal audit caught the natural 88-to-98 display-position shift of Advantage List (stored order 1000). Read-only verification confirmed old fields and relative order unchanged; no existing menu item was edited.';
$receipt['status']='PUBLISHED_AND_SERVER_VERIFIED'; $receipt['completed_utc']=gmdate('c');
file_put_contents(__DIR__.'/publish_receipt.json',wp_json_encode($receipt,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));
echo wp_json_encode($receipt,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
