<?php
// Run only through WP-CLI after a private database backup and package checks.
if (!defined('WP_CLI') || !WP_CLI) { throw new RuntimeException('WP-CLI required'); }
$lock = fopen(__DIR__ . '/publish.lock', 'c');
if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) { throw new RuntimeException('Another publisher holds the lock'); }
$pkg = json_decode(file_get_contents(__DIR__ . '/publish_package.json'), true, 512, JSON_THROW_ON_ERROR);
if (rtrim(home_url(), '/') !== 'https://edukaizen.nl' || $pkg['site'] !== 'https://edukaizen.nl' || count($pkg['pages']) !== 10) { throw new RuntimeException('Wrong site/package'); }
if (!is_file(__DIR__ . '/backup.sql') || filesize(__DIR__ . '/backup.sql') < 1000) { throw new RuntimeException('Private database backup is missing'); }
if (!shortcode_exists('latex')) { throw new RuntimeException('MathJax shortcode is unavailable'); }
$menu_id = 3;
if (!wp_get_nav_menu_object($menu_id)) { throw new RuntimeException('Expected menu missing'); }
global $receipt, $receipt_path;
$receipt_path = __DIR__ . '/publish_receipt.json';
$receipt = ['release' => $pkg['release'], 'status' => 'IN_PROGRESS', 'pages' => [], 'menu_items' => [], 'backup_path' => __DIR__ . '/backup.sql'];
function nh_save_receipt() { global $receipt, $receipt_path; file_put_contents($receipt_path, wp_json_encode($receipt, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)); }
function nh_post_signature($id) {
    $p = get_post($id, ARRAY_A);
    if (!$p) { return null; }
    return hash('sha256', wp_json_encode(array_intersect_key($p, array_flip(['ID','post_title','post_content','post_excerpt','post_name','post_parent','post_status','post_type']))));
}
function nh_menu_snapshot($menu) {
    $out = [];
    foreach (wp_get_nav_menu_items($menu) ?: [] as $m) {
        $out[(string)$m->ID] = ['title'=>$m->title,'url'=>$m->url,'parent'=>(int)$m->menu_item_parent,'order'=>(int)$m->menu_order,'object'=>$m->object,'object_id'=>(int)$m->object_id];
    }
    return $out;
}
$before_posts = [];
foreach (get_posts(['post_type'=>['post','page'],'post_status'=>'any','numberposts'=>-1]) as $p) {
    if (get_post_meta($p->ID, '_nh_series3_owner', true) !== 'nighthawk-series3') { $before_posts[(string)$p->ID] = nh_post_signature($p->ID); }
}
$before_menu = nh_menu_snapshot($menu_id);
file_put_contents(__DIR__.'/before_signatures.json', wp_json_encode(['posts'=>$before_posts,'menu'=>$before_menu], JSON_PRETTY_PRINT));
$ids = [];
foreach ($pkg['pages'] as $entry) {
    $part = (int)$entry['part'];
    $parent = $part === 0 ? 0 : $ids[0];
    if (hash('sha256', $entry['html']) !== $entry['sha256'] || strpos($entry['html'], 'CONCEPT') !== false || strpos($entry['html'], 'hubbard-nighthawk-serie-3/') !== false) { throw new RuntimeException('Content checksum/draft gate'); }
    global $wpdb;
    $matches = $wpdb->get_col($wpdb->prepare("SELECT ID FROM {$wpdb->posts} WHERE post_type='page' AND post_name=%s AND post_parent=%d", $entry['slug'], $parent));
    if (count($matches) > 1) { throw new RuntimeException('Ambiguous page slug'); }
    $id = count($matches) ? (int)$matches[0] : 0;
    if ($id) {
        if (get_post_meta($id, '_nh_series3_owner', true) !== 'nighthawk-series3' || (string)get_post_meta($id, '_nh_series3_part', true) !== (string)$part) { throw new RuntimeException('Refusing to overwrite an unrelated page'); }
        $known = get_post_meta($id, '_nh_series3_content_sha256', true);
        if ($known && hash('sha256', get_post($id)->post_content) !== $known) { throw new RuntimeException('Manual page edit detected; preserve it'); }
    }
    $args = ['post_type'=>'page','post_title'=>$entry['title'],'post_name'=>$entry['slug'],'post_parent'=>$parent,
        'post_content'=>$entry['html'],'post_excerpt'=>$entry['excerpt'],'comment_status'=>'closed','ping_status'=>'closed'];
    if ($id) {
        $args['ID']=$id;
        $result=wp_update_post(wp_slash($args), true);
    } else {
        $args['post_status']='draft';
        $result=wp_insert_post(wp_slash($args), true);
    }
    if (is_wp_error($result)) { throw new RuntimeException($result->get_error_message()); }
    $id=(int)$result; $ids[$part]=$id;
    update_post_meta($id, '_nh_series3_owner', 'nighthawk-series3');
    update_post_meta($id, '_nh_series3_part', (string)$part);
    update_post_meta($id, '_nh_series3_release', $pkg['release']);
    update_post_meta($id, '_nh_series3_content_sha256', $entry['sha256']);
    clean_post_cache($id);
    if (get_post($id)->post_content !== $entry['html'] || get_post($id)->post_name !== $entry['slug']) { throw new RuntimeException('Stored content or slug changed'); }
    $receipt['pages'][]=['part'=>$part,'id'=>$id,'parent'=>$parent,'title'=>$entry['title'],'slug'=>$entry['slug'],'expected_url'=>$entry['url'],'sha256'=>$entry['sha256']];
    nh_save_receipt();
}
foreach ($receipt['pages'] as &$row) {
    $updated=wp_update_post(['ID'=>$row['id'],'post_status'=>'publish'], true);
    if (is_wp_error($updated)) { throw new RuntimeException($updated->get_error_message()); }
    clean_post_cache($row['id']);
    $row['url']=get_permalink($row['id']); $row['status']=get_post_status($row['id']);
    if ($row['url'] !== $row['expected_url'] || $row['status'] !== 'publish' || hash('sha256', get_post($row['id'])->post_content) !== $row['sha256']) { throw new RuntimeException('Published identity/content check failed'); }
    nh_save_receipt();
}
unset($row);
// Add only this new branch. Existing menu item fields and positions stay intact.
$parent_menu=0;
foreach ($pkg['pages'] as $entry) {
    $part=(int)$entry['part']; $page_id=$ids[$part]; $found=[];
    foreach (wp_get_nav_menu_items($menu_id) ?: [] as $item) {
        if ($item->object==='page' && (int)$item->object_id===$page_id && (int)$item->menu_item_parent===($part===0?0:$parent_menu)) { $found[]=$item; }
    }
    if (count($found)>1) { throw new RuntimeException('Duplicate owned menu item'); }
    if ($found) {
        $mid=(int)$found[0]->ID;
        if ($found[0]->title!==$entry['menu_label'] || $found[0]->url!==get_permalink($page_id)) { throw new RuntimeException('Owned menu differs; inspect before changing'); }
    } else {
        $mid=wp_update_nav_menu_item($menu_id,0,['menu-item-title'=>$entry['menu_label'],'menu-item-object'=>'page',
            'menu-item-object-id'=>$page_id,'menu-item-type'=>'post_type','menu-item-url'=>get_permalink($page_id),
            'menu-item-parent-id'=>$part===0?0:$parent_menu,'menu-item-status'=>'publish','menu-item-position'=>0]);
        if (is_wp_error($mid)) { throw new RuntimeException($mid->get_error_message()); }
    }
    if ($part===0) { $parent_menu=$mid; }
    $receipt['menu_items'][]=['part'=>$part,'id'=>(int)$mid,'parent'=>$part===0?0:(int)$parent_menu];
    nh_save_receipt();
}
$after_menu=nh_menu_snapshot($menu_id);
foreach ($before_menu as $id=>$signature) { if (!isset($after_menu[$id]) || $after_menu[$id] !== $signature) { throw new RuntimeException('Unrelated menu changed'); } }
foreach ($before_posts as $id=>$signature) { if (nh_post_signature((int)$id) !== $signature) { throw new RuntimeException('Unrelated page/post changed'); } }
$receipt['unrelated_posts_preserved']=count($before_posts);
$receipt['existing_menu_items_preserved']=count($before_menu);
$receipt['status']='PUBLISHED_AND_SERVER_VERIFIED'; $receipt['completed_utc']=gmdate('c');
nh_save_receipt();
echo wp_json_encode($receipt, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
