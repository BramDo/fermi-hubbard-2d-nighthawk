<?php
// Scoped NL/EN publication with a private backup and incremental receipt.
if (!defined('WP_CLI') || !WP_CLI || rtrim(home_url(),'/')!=='https://edukaizen.nl') { throw new RuntimeException('Wrong context'); }
$lock=fopen(__DIR__.'/publish.lock','c'); if (!$lock || !flock($lock,LOCK_EX|LOCK_NB)) { throw new RuntimeException('Publisher locked'); }
if (!is_file(__DIR__.'/backup.sql') || filesize(__DIR__.'/backup.sql')<1000) { throw new RuntimeException('Missing private database backup'); }
if (!shortcode_exists('latex')) { throw new RuntimeException('MathJax missing'); }
$opts=get_option('nav_menu_options',[]); if (in_array(3,array_map('intval',$opts['auto_add']??[]),true)) { throw new RuntimeException('Menu auto-add must be assessed before publishing'); }
$pkg=json_decode(file_get_contents(__DIR__.'/payload.json'),true,512,JSON_THROW_ON_ERROR);
if (count($pkg['pairs'])!==10) { throw new RuntimeException('Expected ten translation pairs'); }
function nb_save($receipt) { file_put_contents(__DIR__.'/receipt.json',wp_json_encode($receipt,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE)); }
function nb_sig($id) {
    $p=get_post($id,ARRAY_A);
    return hash('sha256',wp_json_encode(array_intersect_key($p,array_flip(['ID','post_title','post_content','post_excerpt','post_name','post_parent','post_status','post_type']))));
}
function nb_menu() {
    $out=[]; foreach (wp_get_nav_menu_items(3) ?: [] as $m) { $out[$m->ID]=[$m->title,$m->url,$m->menu_item_parent,$m->menu_order,$m->object,$m->object_id]; } return $out;
}
$nl_ids=[];
foreach ($pkg['pairs'] as $pair) {
    $nl=$pair['nl']; $p=get_post($nl['id']);
    if (!$p || $p->post_type!=='page' || $p->post_status!=='publish' || $p->post_title!==$nl['title'] || $p->post_name!==$nl['slug'] || (int)$p->post_parent!==$nl['parent'] || hash('sha256',$p->post_content)!==$nl['before_sha256'] || get_permalink($p)!==$nl['url']) { throw new RuntimeException('Dutch page changed since inventory'); }
    foreach (['nl','en'] as $lang) { if (hash('sha256',$pair[$lang]['html'])!==$pair[$lang]['sha256'] || substr_count($pair[$lang]['html'],'<nav class="nh-language-switch"')!==1) { throw new RuntimeException('Invalid language payload'); } }
    $nl_ids[]=(int)$nl['id'];
}
$posts=[]; foreach (get_posts(['post_type'=>['post','page'],'post_status'=>'any','numberposts'=>-1]) as $p) { if (!in_array($p->ID,$nl_ids,true) && get_post_meta($p->ID,'_nh_series3_owner',true)!=='nighthawk-series3-en') { $posts[$p->ID]=nb_sig($p->ID); } }
$menu=nb_menu(); file_put_contents(__DIR__.'/before_signatures.json',wp_json_encode(['posts'=>$posts,'menu'=>$menu],JSON_PRETTY_PRINT));
$receipt=['status'=>'IN_PROGRESS','release'=>$pkg['release'],'pairs'=>[],'backup_path'=>__DIR__.'/backup.sql']; $english_ids=[]; nb_save($receipt);
global $wpdb;
foreach ($pkg['pairs'] as $pair) {
    $part=(int)$pair['part']; $en=$pair['en']; $parent=$part===0?0:$english_ids[0];
    $matches=$wpdb->get_col($wpdb->prepare("SELECT ID FROM {$wpdb->posts} WHERE post_type='page' AND post_name=%s AND post_parent=%d",$en['slug'],$parent));
    if (count($matches)>1) { throw new RuntimeException('Ambiguous English slug'); }
    $id=count($matches)?(int)$matches[0]:0;
    if ($id) {
        if (get_post_meta($id,'_nh_series3_owner',true)!=='nighthawk-series3-en' || (string)get_post_meta($id,'_nh_series3_part',true)!==(string)$part) { throw new RuntimeException('Refusing unrelated English-page overwrite'); }
        $known=get_post_meta($id,'_nh_series3_content_sha256',true);
        if ($known && hash('sha256',get_post($id)->post_content)!==$known) { throw new RuntimeException('Preserve manual English edit'); }
    }
    $args=['post_type'=>'page','post_title'=>$en['title'],'post_name'=>$en['slug'],'post_parent'=>$parent,'post_content'=>$en['html'],'comment_status'=>'closed','ping_status'=>'closed'];
    if ($id) { $args['ID']=$id; $result=wp_update_post(wp_slash($args),true); }
    else { $args['post_status']='draft'; $result=wp_insert_post(wp_slash($args),true); }
    if (is_wp_error($result)) { throw new RuntimeException($result->get_error_message()); }
    $id=(int)$result; $english_ids[$part]=$id;
    update_post_meta($id,'_nh_series3_owner','nighthawk-series3-en'); update_post_meta($id,'_nh_series3_part',(string)$part);
    update_post_meta($id,'_nh_series3_language','en'); update_post_meta($id,'_nh_series3_peer_id',(int)$pair['nl']['id']); update_post_meta($id,'_nh_series3_content_sha256',$en['sha256']);
    if (get_post($id)->post_content!==$en['html'] || get_post($id)->post_name!==$en['slug']) { throw new RuntimeException('English storage check failed'); }
    $receipt['pairs'][]=['part'=>$part,'en'=>['id'=>$id,'parent'=>$parent,'url'=>$en['url'],'title'=>$en['title'],'sha256'=>$en['sha256']],'nl'=>['id'=>$pair['nl']['id'],'url'=>$pair['nl']['url'],'before_sha256'=>$pair['nl']['before_sha256'],'sha256'=>$pair['nl']['sha256']]]; nb_save($receipt);
}
foreach ($receipt['pairs'] as &$row) {
    $id=$row['en']['id']; $result=wp_update_post(['ID'=>$id,'post_status'=>'publish'],true);
    if (is_wp_error($result)) { throw new RuntimeException($result->get_error_message()); }
    clean_post_cache($id);
    if (get_permalink($id)!==$row['en']['url'] || hash('sha256',get_post($id)->post_content)!==$row['en']['sha256']) { throw new RuntimeException('English public identity/content failed'); }
    $row['en']['status']='publish'; nb_save($receipt);
}
unset($row);
foreach ($pkg['pairs'] as $pair) {
    $nl=$pair['nl']; $id=(int)$nl['id']; clean_post_cache($id);
    if (hash('sha256',get_post($id)->post_content)!==$nl['before_sha256']) { throw new RuntimeException('Dutch concurrent edit detected'); }
    $result=wp_update_post(wp_slash(['ID'=>$id,'post_content'=>$nl['html']]),true);
    if (is_wp_error($result)) { throw new RuntimeException($result->get_error_message()); }
    update_post_meta($id,'_nh_series3_language','nl'); update_post_meta($id,'_nh_series3_peer_id',$english_ids[$pair['part']]); update_post_meta($id,'_nh_series3_content_sha256',$nl['sha256']);
    clean_post_cache($id);
    if (get_permalink($id)!==$nl['url'] || get_post($id)->post_content!==$nl['html']) { throw new RuntimeException('Dutch storage/permalink failed'); }
    $receipt['pairs'][$pair['part']]['nl']['status']='publish'; nb_save($receipt);
}
if (nb_menu()!==$menu) { throw new RuntimeException('Navigation changed unexpectedly'); }
foreach ($posts as $id=>$signature) { if (nb_sig((int)$id)!==$signature) { throw new RuntimeException('Unrelated post changed'); } }
$receipt['status']='BILINGUAL_PUBLISHED_AND_SERVER_VERIFIED'; $receipt['menu_unchanged']=true; $receipt['menu_items_preserved']=count($menu); $receipt['unrelated_posts_preserved']=count($posts); $receipt['completed_utc']=gmdate('c'); nb_save($receipt);
echo wp_json_encode($receipt,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
