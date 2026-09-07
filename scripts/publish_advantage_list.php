<?php
if (!defined('WP_CLI') || !WP_CLI || rtrim(home_url(),'/')!=='https://edukaizen.nl') { throw new RuntimeException('Wrong context'); }
if (!is_file(__DIR__.'/backup.sql') || filesize(__DIR__.'/backup.sql')<1000) { throw new RuntimeException('Private backup missing'); }
$lock=fopen(__DIR__.'/publish.lock','c'); if (!$lock || !flock($lock,LOCK_EX|LOCK_NB)) { throw new RuntimeException('Publisher busy'); }
$pkg=json_decode(file_get_contents(__DIR__.'/payload.json'),true,512,JSON_THROW_ON_ERROR);
$target=get_post(451);
if (!$target || $target->post_name!=='pro-student-quantum-advantage-list' || $target->post_status!=='publish' || hash('sha256',$target->post_content)!==$pkg['before_sha256']) { throw new RuntimeException('Target content changed; preserve concurrent edits'); }
if (hash('sha256',$pkg['html'])!==$pkg['after_sha256'] || substr_count($pkg['html'],'id="fermi-hubbard-2d-nighthawk-72q"')!==1) { throw new RuntimeException('Invalid payload'); }
function al_sig($id) {
    $p=get_post($id,ARRAY_A);
    return hash('sha256',wp_json_encode(array_intersect_key($p,array_flip(['ID','post_title','post_content','post_excerpt','post_name','post_parent','post_status','post_type']))));
}
function al_menu() {
    $out=[]; foreach (wp_get_nav_menu_items(3) ?: [] as $m) { $out[$m->ID]=[$m->title,$m->url,$m->menu_item_parent,$m->menu_order,$m->object,$m->object_id]; }
    return $out;
}
$old_menu=al_menu(); $posts=[];
foreach (get_posts(['post_type'=>['post','page'],'post_status'=>'any','numberposts'=>-1]) as $p) { if ($p->ID!==451) { $posts[$p->ID]=al_sig($p->ID); } }
file_put_contents(__DIR__.'/before.json',wp_json_encode(['target'=>$target,'other_signatures'=>$posts,'menu'=>$old_menu],JSON_PRETTY_PRINT));
$result=wp_update_post(wp_slash(['ID'=>451,'post_content'=>$pkg['html']]),true);
if (is_wp_error($result)) { throw new RuntimeException($result->get_error_message()); }
clean_post_cache(451);
if (hash('sha256',get_post(451)->post_content)!==$pkg['after_sha256'] || get_permalink(451)!=='https://edukaizen.nl/pro-student-quantum-advantage-list/') { throw new RuntimeException('Content/permalink verification failed'); }
if (al_menu()!==$old_menu) { throw new RuntimeException('Menu changed'); }
foreach ($posts as $id=>$sig) { if (al_sig((int)$id)!==$sig) { throw new RuntimeException('Other post changed'); } }
$receipt=['status'=>'PUBLISHED_AND_SERVER_VERIFIED','page_id'=>451,'url'=>get_permalink(451),'before_sha256'=>$pkg['before_sha256'],'after_sha256'=>$pkg['after_sha256'],'other_posts_preserved'=>count($posts),'menu_items_preserved'=>count($old_menu),'entry_count'=>7,'completed_utc'=>gmdate('c'),'backup_path'=>__DIR__.'/backup.sql'];
file_put_contents(__DIR__.'/receipt.json',wp_json_encode($receipt,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES));
echo wp_json_encode($receipt,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES);
