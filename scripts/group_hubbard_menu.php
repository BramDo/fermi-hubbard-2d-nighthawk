<?php
// Authorized navigation-only change; existing pages and article URLs stay intact.
if (!defined('WP_CLI') || !WP_CLI || rtrim(home_url(),'/')!=='https://edukaizen.nl') { throw new RuntimeException('Wrong execution context'); }
if (!is_file(__DIR__.'/backup.sql') || filesize(__DIR__.'/backup.sql')<1000) { throw new RuntimeException('Missing private backup'); }
$lock=fopen(__DIR__.'/navigation.lock','c');
if (!$lock || !flock($lock,LOCK_EX|LOCK_NB)) { throw new RuntimeException('Navigation lock busy'); }
$menu_id=3; $branches=[332,373,1109];
function hg_snapshot($menu) {
    $out=[];
    foreach (wp_get_nav_menu_items($menu) ?: [] as $m) {
        $out[(string)$m->ID]=['title'=>$m->title,'url'=>$m->url,'parent'=>(int)$m->menu_item_parent,'object'=>$m->object,'object_id'=>(int)$m->object_id,'type'=>$m->type,'target'=>$m->target,'attr_title'=>$m->attr_title,'description'=>$m->description,'classes'=>$m->classes,'xfn'=>$m->xfn,'stored_order'=>(int)get_post($m->ID)->menu_order];
    }
    return $out;
}
function hg_post_signature($id) {
    $p=get_post($id,ARRAY_A);
    return hash('sha256',wp_json_encode(array_intersect_key($p,array_flip(['ID','post_title','post_content','post_excerpt','post_name','post_parent','post_status','post_type']))));
}
function hg_save($receipt) { file_put_contents(__DIR__.'/navigation_receipt.json',wp_json_encode($receipt,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE)); }
$before=hg_snapshot($menu_id);
if (count($before)!==98) { throw new RuntimeException('Menu changed since inventory'); }
foreach ($before as $id=>$m) { if ($m['title']==='Hubbard' && $m['parent']===0) { throw new RuntimeException('Hubbard grouping already exists; do not duplicate'); } }
foreach ([332=>['Hubbard 1D',331,'post_type','https://edukaizen.nl/fermi-hubbard-quantum-simulation-project/'],373=>['Hubbard 2D',373,'custom','https://edukaizen.nl/fermi-hubbard-2d-cuprate-series/'],1109=>['2D Local Quantum Advantage',1089,'post_type','https://edukaizen.nl/2d-local-quantum-advantage/']] as $id=>$expected) {
    if (!isset($before[$id]) || $before[$id]['title']!==$expected[0] || $before[$id]['object_id']!==$expected[1] || $before[$id]['type']!==$expected[2] || $before[$id]['url']!==$expected[3] || $before[$id]['parent']!==0) { throw new RuntimeException('Unexpected series identity'); }
}
$posts=[]; foreach (get_posts(['post_type'=>['post','page'],'post_status'=>'any','numberposts'=>-1]) as $p) { $posts[$p->ID]=hg_post_signature($p->ID); }
file_put_contents(__DIR__.'/navigation_before.json',wp_json_encode(['menu'=>$before,'post_signatures'=>$posts],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES));
$group=wp_update_nav_menu_item($menu_id,0,['menu-item-title'=>'Hubbard','menu-item-type'=>'custom','menu-item-url'=>'#','menu-item-parent-id'=>0,'menu-item-position'=>2,'menu-item-status'=>'publish']);
if (is_wp_error($group)) { throw new RuntimeException($group->get_error_message()); }
update_post_meta($group,'_hubbard_menu_group_owner','series3-2026-09-07');
$receipt=['status'=>'IN_PROGRESS','group_id'=>(int)$group,'group_label'=>'Hubbard','group_url'=>'#','branches'=>[],'backup_path'=>__DIR__.'/backup.sql']; hg_save($receipt);
foreach ($branches as $id) {
    $m=$before[$id];
    // Supply the complete menu-item fields; only its parent is intentionally new.
    $result=wp_update_nav_menu_item($menu_id,$id,['menu-item-title'=>$m['title'],'menu-item-url'=>$m['url'],'menu-item-object'=>$m['object'],'menu-item-object-id'=>$m['object_id'],'menu-item-type'=>$m['type'],'menu-item-target'=>$m['target'],'menu-item-attr-title'=>$m['attr_title'],'menu-item-description'=>$m['description'],'menu-item-classes'=>implode(' ',$m['classes']),'menu-item-xfn'=>$m['xfn'],'menu-item-parent-id'=>$group,'menu-item-position'=>$m['stored_order'],'menu-item-status'=>'publish']);
    if (is_wp_error($result)) { throw new RuntimeException($result->get_error_message()); }
    $receipt['branches'][]=['id'=>$id,'title'=>$m['title'],'parent'=>(int)$group,'url'=>$m['url']]; hg_save($receipt);
}
$after=hg_snapshot($menu_id);
if (count($after)!==99) { throw new RuntimeException('Unexpected final menu count'); }
foreach ($before as $id=>$expected) {
    if (in_array((int)$id,$branches,true)) { $expected['parent']=(int)$group; }
    if (!isset($after[$id]) || $after[$id]!==$expected) { throw new RuntimeException('Unexpected existing menu field change for '.$id); }
}
foreach ($posts as $id=>$signature) { if (hg_post_signature((int)$id)!==$signature) { throw new RuntimeException('Page content changed'); } }
$children=[]; foreach ($after as $id=>$m) { if ($m['parent']===(int)$group) { $children[]=(int)$id; } }
if ($children!==$branches) { throw new RuntimeException('Wrong series order'); }
if ($after[452]['parent']!==0 || $after[452]['stored_order']!==1000) { throw new RuntimeException('Advantage List changed'); }
$receipt['status']='GROUPED_AND_SERVER_VERIFIED'; $receipt['pages_preserved']=count($posts); $receipt['existing_menu_items_preserved']=count($before);
$receipt['only_existing_parent_changes']=$branches; $receipt['all_existing_stored_orders_preserved']=true; $receipt['completed_utc']=gmdate('c'); $receipt['menu_before']=$before; $receipt['menu_after']=$after;
hg_save($receipt); echo wp_json_encode($receipt,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
