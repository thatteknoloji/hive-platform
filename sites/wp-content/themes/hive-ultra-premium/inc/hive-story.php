<?php
/**
 * Hikaye (Story) modülü – 24 saat aktif
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

define('HIVE_STORY_TTL', DAY_IN_SECONDS);

add_action('init', 'hive_register_story_cpt');
function hive_register_story_cpt() {
    register_post_type('story', array(
        'labels' => array(
            'name'          => __('Hikayeler', 'hive-ultra-premium'),
            'singular_name' => __('Hikaye', 'hive-ultra-premium'),
            'add_new_item'  => __('Yeni Hikaye Ekle', 'hive-ultra-premium'),
            'edit_item'     => __('Hikayeyi Düzenle', 'hive-ultra-premium'),
        ),
        'public'       => true,
        'has_archive'  => false,
        'show_in_rest' => true,
        'menu_icon'    => 'dashicons-instagram',
        'supports'     => array('title', 'editor', 'thumbnail'),
        'rewrite'      => false,
    ));
}

add_action('add_meta_boxes', 'hive_story_metabox');
function hive_story_metabox() {
    add_meta_box(
        'hive_story_details',
        __('Hikaye Detayları', 'hive-ultra-premium'),
        'hive_story_metabox_callback',
        'story',
        'normal',
        'high'
    );
}

function hive_story_metabox_callback($post) {
    wp_nonce_field('hive_story_save', 'hive_story_nonce');
    $lokasyon   = get_post_meta($post->ID, 'lokasyon', true);
    $profile_id = get_post_meta($post->ID, '_story_profile_id', true);
    $expires    = get_post_meta($post->ID, '_story_expires', true);

    echo '<p><label><strong>' . esc_html__('Lokasyon', 'hive-ultra-premium') . '</strong></label><br>';
    echo '<input type="text" name="story_lokasyon" value="' . esc_attr($lokasyon) . '" style="width:100%;" placeholder="Kadınlar Denizi, Kuşadası"></p>';

    echo '<p><label><strong>' . esc_html__('Bağlı profil (opsiyonel)', 'hive-ultra-premium') . '</strong></label><br>';
    echo '<select name="story_profile_id" style="width:100%;"><option value="">' . esc_html__('Genel hikaye', 'hive-ultra-premium') . '</option>';
    $profiles = get_posts(array('post_type' => 'companion_profile', 'posts_per_page' => 100, 'orderby' => 'title', 'order' => 'ASC'));
    foreach ($profiles as $p) {
        echo '<option value="' . esc_attr($p->ID) . '" ' . selected($profile_id, $p->ID, false) . '>' . esc_html($p->post_title) . '</option>';
    }
    echo '</select></p>';

    if ($expires) {
        echo '<p class="description">' . esc_html__('Bitiş:', 'hive-ultra-premium') . ' ' . esc_html(date_i18n('d.m.Y H:i', (int) $expires)) . '</p>';
    }
    echo '<p class="description">' . esc_html__('Öne çıkan görsel = hikaye avatarı. 24 saat sonra otomatik arşivlenir.', 'hive-ultra-premium') . '</p>';
}

add_action('save_post_story', 'hive_save_story');
function hive_save_story($post_id) {
    if (!isset($_POST['hive_story_nonce']) || !wp_verify_nonce($_POST['hive_story_nonce'], 'hive_story_save')) {
        return;
    }
    if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) {
        return;
    }
    if (!current_user_can('edit_post', $post_id)) {
        return;
    }

    if (isset($_POST['story_lokasyon'])) {
        update_post_meta($post_id, 'lokasyon', sanitize_text_field($_POST['story_lokasyon']));
    }
    if (isset($_POST['story_profile_id'])) {
        $pid = (int) $_POST['story_profile_id'];
        if ($pid) {
            update_post_meta($post_id, '_story_profile_id', $pid);
        } else {
            delete_post_meta($post_id, '_story_profile_id');
        }
    }

    $status = get_post_status($post_id);
    if ($status === 'publish' && !get_post_meta($post_id, '_story_expires', true)) {
        update_post_meta($post_id, '_story_expires', time() + HIVE_STORY_TTL);
    }
}

/**
 * Hikaye GIF / görsel URL'leri
 */
function hive_story_gif_url($post_id) {
    $url = get_post_meta($post_id, '_story_gif_url', true);
    if ($url) {
        return esc_url($url);
    }
    $full = get_the_post_thumbnail_url($post_id, 'full');
    return $full ? esc_url($full) : '';
}

function hive_story_ring_url($post_id) {
    $gif = hive_story_gif_url($post_id);
    if ($gif) {
        return $gif;
    }
    $thumb = get_the_post_thumbnail_url($post_id, 'hive-profile-thumb');
    return $thumb ? esc_url($thumb) : hive_ultra_placeholder_url();
}

/**
 * Aktif hikayeler sorgusu (kalıcı + süresi dolmamış)
 */
function hive_get_active_stories($profile_id = null, $limit = 24) {
    $meta = array(
        'relation' => 'OR',
        array(
            'key'     => '_story_permanent',
            'value'   => '1',
            'compare' => '=',
        ),
        array(
            'relation' => 'AND',
            array(
                'key'     => '_story_expires',
                'value'   => time(),
                'compare' => '>',
                'type'    => 'NUMERIC',
            ),
            array(
                'relation' => 'OR',
                array(
                    'key'     => '_story_permanent',
                    'compare' => 'NOT EXISTS',
                ),
                array(
                    'key'     => '_story_permanent',
                    'value'   => '1',
                    'compare' => '!=',
                ),
            ),
        ),
    );

    if ($profile_id) {
        $meta = array(
            'relation' => 'AND',
            $meta,
            array(
                'relation' => 'OR',
                array(
                    'key'     => '_story_profile_id',
                    'value'   => (int) $profile_id,
                    'compare' => '=',
                ),
                array(
                    'key'     => '_story_profile_id',
                    'compare' => 'NOT EXISTS',
                ),
            ),
        );
    }

    return new WP_Query(array(
        'post_type'      => 'story',
        'posts_per_page' => (int) $limit,
        'orderby'        => 'menu_order date',
        'order'          => 'ASC',
        'meta_query'     => $meta,
    ));
}

/**
 * Süresi dolan hikayeleri arşivle
 */
add_action('hive_expire_stories_cron', 'hive_expire_stories');
function hive_expire_stories() {
    $expired = get_posts(array(
        'post_type'      => 'story',
        'posts_per_page' => 50,
        'post_status'    => 'publish',
        'meta_query'     => array(
            array(
                'key'     => '_story_expires',
                'value'   => time(),
                'compare' => '<',
                'type'    => 'NUMERIC',
            ),
        ),
    ));
    foreach ($expired as $post) {
        if (get_post_meta($post->ID, '_story_permanent', true) === '1') {
            continue;
        }
        wp_trash_post($post->ID);
    }
}

/**
 * Varsayılan Instagram hikayeleri — 24 sexy GIF (bir kez seed)
 */
function hive_seed_instagram_stories() {
    if ((int) get_option('hive_ig_stories_v3') === 1) {
        return;
    }
    if (get_transient('hive_ig_stories_seeding')) {
        return;
    }

    $existing = (int) count(get_posts(array(
        'post_type'      => 'story',
        'posts_per_page' => -1,
        'post_status'    => 'publish',
        'fields'         => 'ids',
        'meta_query'     => array(
            array(
                'key'     => '_story_seeded',
                'value'   => '1',
                'compare' => '=',
            ),
        ),
    )));
    set_transient('hive_ig_stories_seeding', 1, 20 * MINUTE_IN_SECONDS);
    update_option('hive_ig_stories_v3', 'seeding');

    $legacy = get_posts(array(
        'post_type'      => 'story',
        'posts_per_page' => -1,
        'post_status'    => array('publish', 'draft', 'trash'),
        'fields'         => 'ids',
    ));
    foreach ($legacy as $pid) {
        wp_delete_post($pid, true);
    }

    require_once ABSPATH . 'wp-admin/includes/file.php';
    require_once ABSPATH . 'wp-admin/includes/media.php';
    require_once ABSPATH . 'wp-admin/includes/image.php';

    $items = array(
        array('title' => 'Aylin 🔥', 'loc' => 'Kuşadası, Kadınlar Denizi', 'gif' => 'CZedlPSpZ6hKo', 'text' => 'Bu gece özel görünüm ✨'),
        array('title' => 'Selin 💋', 'loc' => 'Kuşadası, Yılancı Burnu', 'gif' => 'k3c1eZexGrYaYPYXJg', 'text' => 'Sıcak bir bakış seni bekliyor…'),
        array('title' => 'Ruby VIP', 'loc' => 'Kuşadası Merkez', 'gif' => 'BSMHwm6puaMX6', 'text' => 'VIP deneyim için mesaj at 💎'),
        array('title' => 'Luna 🌙', 'loc' => 'Kuşadası, Güvercinada', 'gif' => 'vGXrAWGlbR8kw', 'text' => 'Gece modu aktif…'),
        array('title' => 'Melis 😘', 'loc' => 'Kuşadası, Davutlar', 'gif' => 'WWnyPSQDjQDIc', 'text' => 'Flörtöz bir selam gönderiyorum'),
        array('title' => 'Honey', 'loc' => 'Kuşadası, Türkmen', 'gif' => 'X8XEgX7YYVfkQ', 'text' => 'Tatlı ama cesur 💫'),
        array('title' => 'Derya', 'loc' => 'Kuşadası, Cumhuriyet', 'gif' => '5DKmrHwVHcv7y', 'text' => 'Yeni fotoğraflar yüklendi 📸'),
        array('title' => 'Bella', 'loc' => 'Kuşadası, Hacıfeyzullah', 'gif' => 'hZe3vds14VDWXjM15l', 'text' => 'Özel davet — sadece bugün'),
        array('title' => 'Ceyda', 'loc' => 'Kuşadası, Camiatik', 'gif' => 'nWq9Ry6NzcC21kMy7O', 'text' => 'Kuşadası gecesi başlasın 🌴'),
        array('title' => 'Elif', 'loc' => 'Kuşadası, Karaova', 'gif' => 'yLFLXEpQkx1JAqCtZC', 'text' => 'Cesur ve özgür ruh 🔥'),
        array('title' => 'Deniz Kızı', 'loc' => 'Kadınlar Denizi', 'gif' => 'P5aPELJ9sCxfnsZzB1', 'text' => 'Plaj havasında…'),
        array('title' => 'Palmiye', 'loc' => 'Kuşadası, Yavansu', 'gif' => 'C8whbwowXFi3iJCEOG', 'text' => 'Tropik enerji 🌺'),
        array('title' => 'Gece Modu', 'loc' => 'Kuşadası Merkez', 'gif' => '3o7TKSjRrfIPjeiVy', 'text' => 'Gece hayatına hazır mısın?'),
        array('title' => 'Özel An', 'loc' => 'Kuşadası, Güzelçamlı', 'gif' => 'elhmwUMsAUbScKLLzl', 'text' => 'Sadece seçkin ziyaretçiler'),
        array('title' => 'Love Island', 'loc' => 'Kuşadası', 'gif' => 'mHkYRG7JUNUQGeqDXp', 'text' => 'Romantik bir akşam…'),
        array('title' => 'Jessica', 'loc' => 'Kuşadası, Kadınlar Denizi', 'gif' => 'TEQH45vIQHTmE', 'text' => 'Göz teması kur 🔥'),
        array('title' => 'Cherry', 'loc' => 'Kuşadası, Yılancı Burnu', 'gif' => '11aFKk8feaOvLi', 'text' => 'Tatlı bir sürpriz'),
        array('title' => 'Öpücük', 'loc' => 'Kuşadası', 'gif' => 'jq6kmuX9JASsg', 'text' => 'Sana bir öpücük gönderdim 💋'),
        array('title' => 'Mood', 'loc' => 'Kuşadası Merkez', 'gif' => '8qABb3dgjun8PdNirg', 'text' => 'Bugünkü ruh halim…'),
        array('title' => 'Bikini', 'loc' => 'Kadınlar Denizi', 'gif' => '3orieN4j2Rp3eaYsSY', 'text' => 'Yaz enerjisi devam ediyor ☀️'),
        array('title' => 'Plaj', 'loc' => 'Kuşadası, Davutlar', 'gif' => '3oz8xDHBNdFL02tPEc', 'text' => 'Deniz kenarında buluşma?'),
        array('title' => 'Star', 'loc' => 'Kuşadası, Güvercinada', 'gif' => '5jD8KQRMb1GwhYczP7', 'text' => 'Parlayan bir gece ✨'),
        array('title' => 'Velvet', 'loc' => 'Kuşadası, Türkmen', 'gif' => '6dEcB4YDVW9OasYjYn', 'text' => 'Kadife dokunuş hissi'),
        array('title' => 'Pearl', 'loc' => 'Kuşadası, Cumhuriyet', 'gif' => 'BVgiGxBLbuMzC', 'text' => 'İnci gibi özel deneyim'),
        array('title' => 'Lace', 'loc' => 'Kuşadası, Kadınlar Denizi', 'gif' => '26xBthJnvnixIr8JO', 'text' => 'Dantel detaylar…'),
        array('title' => 'Silk', 'loc' => 'Kuşadası Merkez', 'gif' => '4faeIqSKfqrBLvPpwq', 'text' => 'İpek dokunuş hissi'),
        array('title' => 'Noir', 'loc' => 'Kuşadası, Yılancı Burnu', 'gif' => '4lVllhvljDz90jNMUs', 'text' => 'Karanlık ve çekici 🖤'),
        array('title' => 'Rose', 'loc' => 'Kuşadası, Güvercinada', 'gif' => '4ooW6lpLjnFeKLCiQD', 'text' => 'Gül gibi zarif'),
        array('title' => 'Siren', 'loc' => 'Kuşadası, Davutlar', 'gif' => '5MjtQcANX6OodsRnLJ', 'text' => 'Denizden gelen çağrı'),
        array('title' => 'Violet', 'loc' => 'Kuşadası, Türkmen', 'gif' => '8R6P6VAXwbTn8b3sUN', 'text' => 'Mor gecenin sırrı'),
        array('title' => 'Crimson', 'loc' => 'Kuşadası, Cumhuriyet', 'gif' => 'BKH9KihUPqG2Y', 'text' => 'Kırmızı tutku'),
        array('title' => 'Jade', 'loc' => 'Kuşadası, Camiatik', 'gif' => 'JExVqLpo8ztnfwlQd2', 'text' => 'Yeşil gözler seni izliyor'),
        array('title' => 'Amber', 'loc' => 'Kuşadası, Karaova', 'gif' => 'LcY29T28Y6tWRFZfTe', 'text' => 'Altın saat yaklaşıyor'),
        array('title' => 'Scarlet', 'loc' => 'Kuşadası, Yavansu', 'gif' => 'Oc9Z8dbzgiEKdy5Kxd', 'text' => 'Cesur kırmızı'),
        array('title' => 'Ivory', 'loc' => 'Kuşadası, Güzelçamlı', 'gif' => 'PWBjMGVV8hxTi', 'text' => 'Saf ve çekici'),
        array('title' => 'Onyx', 'loc' => 'Kuşadası Merkez', 'gif' => 'SnTN2B8rHyTPhY5Idv', 'text' => 'Siyah elbise, gece hazır'),
        array('title' => 'Coral', 'loc' => 'Kadınlar Denizi', 'gif' => 'Ta6XCNSXcdamsNFtPq', 'text' => 'Mercan rengi yaz'),
        array('title' => 'Mystic', 'loc' => 'Kuşadası, Kadınlar Denizi', 'gif' => 'YusDmqKUwdIGJym16Q', 'text' => 'Gizemli bir bakış'),
        array('title' => 'Blaze', 'loc' => 'Kuşadası, Yılancı Burnu', 'gif' => 'dV2NxXKsLnyG39Mw23', 'text' => 'Alev gibi enerji'),
        array('title' => 'Gloss', 'loc' => 'Kuşadası Merkez', 'gif' => 'ftLEmHEevX04QX4J3Y', 'text' => 'Parlak dudaklar 💄'),
        array('title' => 'Velour', 'loc' => 'Kuşadası, Güvercinada', 'gif' => 'fvH3KrpxVH7uKtFgvD', 'text' => 'Kadife ten'),
        array('title' => 'Satin', 'loc' => 'Kuşadası, Davutlar', 'gif' => 'lBIRm4XGHpVtrD5DxA', 'text' => 'Saten gecelik'),
        array('title' => 'Tempt', 'loc' => 'Kuşadası, Türkmen', 'gif' => 'screugvMjTBjJ4bqgl', 'text' => 'Baştan çıkarıcı an'),
        array('title' => 'Glow', 'loc' => 'Kuşadası, Cumhuriyet', 'gif' => 'w3xgfp6hFgzao', 'text' => 'Işıltılı cilt'),
        array('title' => 'Fox', 'loc' => 'Kuşadası, Camiatik', 'gif' => 'wRZaIhjJckmZZHGaDF', 'text' => 'Tilki bakışı 🦊'),
        array('title' => 'Kiss', 'loc' => 'Kuşadası, Karaova', 'gif' => 'y9b4QeK13CoGk', 'text' => 'Öp beni'),
        array('title' => 'Night', 'loc' => 'Kuşadası Merkez', 'gif' => 'z0LM9Qbl77INC3b8ig', 'text' => 'Gece başlıyor'),
    );

    $seen = array();
    $items = array_values(array_filter($items, function ($item) use (&$seen) {
        if (isset($seen[$item['gif']])) {
            return false;
        }
        $seen[$item['gif']] = true;
        return true;
    }));
    $items = array_slice($items, 0, 24);

    $order = 0;
    foreach ($items as $item) {
        $gif_url = 'https://media.giphy.com/media/' . $item['gif'] . '/giphy.gif';

        $tmp = download_url($gif_url, 30);
        $att_id = 0;
        if (!is_wp_error($tmp)) {
            $file = array(
                'name'     => 'story-' . $item['gif'] . '.gif',
                'tmp_name' => $tmp,
            );
            $att_id = media_handle_sideload($file, 0, $item['title']);
            if (is_wp_error($att_id)) {
                $att_id = 0;
            }
        }

        $post_id = wp_insert_post(array(
            'post_type'    => 'story',
            'post_status'  => 'publish',
            'post_title'   => $item['title'],
            'post_content' => $item['text'],
            'menu_order'   => $order++,
        ), true);

        if (is_wp_error($post_id)) {
            continue;
        }

        if ($att_id) {
            set_post_thumbnail($post_id, $att_id);
            $local = wp_get_attachment_url($att_id);
            if ($local) {
                $gif_url = $local;
            }
        }

        update_post_meta($post_id, 'lokasyon', $item['loc']);
        update_post_meta($post_id, '_story_gif_url', $gif_url);
        update_post_meta($post_id, '_story_giphy_id', $item['gif']);
        update_post_meta($post_id, '_story_permanent', '1');
        update_post_meta($post_id, '_story_seeded', '1');
    }

    update_option('hive_ig_stories_v3', 1);
    delete_transient('hive_ig_stories_seeding');
}

add_action('init', 'hive_schedule_story_cron');
function hive_schedule_story_cron() {
    if (!wp_next_scheduled('hive_expire_stories_cron')) {
        wp_schedule_event(time(), 'hourly', 'hive_expire_stories_cron');
    }
}

/**
 * Story viewer modal (footer)
 */
add_action('wp_footer', 'hive_story_modal_markup');
function hive_story_modal_markup() {
    if (!is_front_page() && !is_singular('companion_profile')) {
        return;
    }
    ?>
    <div id="hive-story-modal" class="hive-story-modal" hidden aria-hidden="true" role="dialog" aria-label="<?php esc_attr_e('Hikaye', 'hive-ultra-premium'); ?>">
        <div class="hive-story-modal-backdrop"></div>
        <div class="hive-story-modal-card">
            <button type="button" class="hive-story-modal-close" aria-label="<?php esc_attr_e('Kapat', 'hive-ultra-premium'); ?>">×</button>
            <div class="hive-story-modal-image-wrap">
                <img id="hive-story-modal-img" src="" alt="">
            </div>
            <div class="hive-story-modal-body">
                <h3 id="hive-story-modal-title"></h3>
                <p id="hive-story-modal-text"></p>
                <span id="hive-story-modal-location" class="story-location"></span>
            </div>
        </div>
    </div>
    <?php
}
