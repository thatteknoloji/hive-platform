<?php
/**
 * Tinder tarzı swipe — REST API, teklif, Telegram
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Profil → JSON
 */
function hive_swipe_format_profile($post_id) {
    $post = get_post($post_id);
    if (!$post || $post->post_type !== 'companion_profile' || $post->post_status !== 'publish') {
        return null;
    }
    $image = get_the_post_thumbnail_url($post_id, 'hive-profile-card');
    if (!$image) {
        $image = hive_ultra_placeholder_url();
    }
    return array(
        'id'       => (int) $post_id,
        'name'     => get_the_title($post_id),
        'age'      => hive_ultra_get_meta($post_id, 'yas'),
        'location' => hive_ultra_get_meta($post_id, 'lokasyon') ?: 'Kuşadası',
        'price'    => hive_ultra_get_meta($post_id, 'fiyat'),
        'image'    => $image,
        'url'      => get_permalink($post_id),
        'vip'      => get_post_meta($post_id, 'vip', true) === '1',
        'matched'  => hive_swipe_is_match($post_id),
    );
}

/**
 * Çift taraflı eşleşme (escort kullanıcıyı da beğenmişse)
 */
function hive_swipe_is_match($profile_id) {
    if (!is_user_logged_in()) {
        return false;
    }
    $uid = get_current_user_id();
    $liked_by_profile = get_post_meta($profile_id, 'hive_liked_users', true);
    if (!is_array($liked_by_profile)) {
        return false;
    }
    return in_array($uid, array_map('intval', $liked_by_profile), true);
}

/**
 * Sıradaki profiller
 */
function hive_swipe_next_profiles(WP_REST_Request $request) {
    $exclude = $request->get_param('exclude');
    $exclude_ids = array();
    if ($exclude) {
        $exclude_ids = array_filter(array_map('intval', explode(',', (string) $exclude)));
    }

    $callback = function () use ($exclude_ids) {
        $q = new WP_Query(array(
            'post_type'      => 'companion_profile',
            'posts_per_page' => 20,
            'orderby'        => 'rand',
            'post_status'    => 'publish',
            'post__not_in'   => $exclude_ids,
            'meta_query'     => array(
                array(
                    'key'     => '_thumbnail_id',
                    'compare' => 'EXISTS',
                ),
                array(
                    'key'     => '_thumbnail_id',
                    'value'   => '0',
                    'compare' => '!=',
                ),
            ),
        ));
        $out = array();
        while ($q->have_posts()) {
            $q->the_post();
            $row = hive_swipe_format_profile(get_the_ID());
            if ($row) {
                $out[] = $row;
            }
        }
        wp_reset_postdata();
        return $out;
    };

    if (is_multisite() && !hive_is_main_site()) {
        switch_to_blog(1);
        $profiles = $callback();
        restore_current_blog();
    } else {
        $profiles = $callback();
    }

    return rest_ensure_response(array(
        'profiles' => $profiles,
        'has_more' => !empty($profiles),
    ));
}

/**
 * Like / dislike kaydet
 */
function hive_swipe_record(WP_REST_Request $request) {
    $profile_id = (int) $request->get_param('profile_id');
    $action     = sanitize_key((string) $request->get_param('action'));

    if (!$profile_id || !in_array($action, array('like', 'dislike'), true)) {
        return new WP_Error('invalid', __('Geçersiz istek.', 'hive-ultra-premium'), array('status' => 400));
    }

    $post = get_post($profile_id);
    if (!$post || $post->post_type !== 'companion_profile') {
        return new WP_Error('not_found', __('Profil bulunamadı.', 'hive-ultra-premium'), array('status' => 404));
    }

    if (is_user_logged_in()) {
        $uid    = get_current_user_id();
        $swipes = get_user_meta($uid, 'hive_swipes', true);
        if (!is_array($swipes)) {
            $swipes = array();
        }
        $swipes[$profile_id] = array(
            'action' => $action,
            'time'   => time(),
        );
        update_user_meta($uid, 'hive_swipes', $swipes);

        if ($action === 'like') {
            $likes = get_post_meta($profile_id, 'hive_user_likes', true);
            if (!is_array($likes)) {
                $likes = array();
            }
            $likes[$uid] = time();
            update_post_meta($profile_id, 'hive_user_likes', $likes);
        }
    }

    return rest_ensure_response(array(
        'ok'      => true,
        'action'  => $action,
        'matched' => $action === 'like' ? hive_swipe_is_match($profile_id) : false,
        'show_offer' => $action === 'like',
    ));
}

/**
 * Teklif gönder
 */
function hive_swipe_send_offer(WP_REST_Request $request) {
    $profile_id = (int) $request->get_param('profile_id');
    $message    = sanitize_textarea_field((string) $request->get_param('message'));

    if (!$profile_id || strlen(trim($message)) < 3) {
        return new WP_Error('invalid', __('Mesaj en az 3 karakter olmalı.', 'hive-ultra-premium'), array('status' => 400));
    }

    $post = get_post($profile_id);
    if (!$post || $post->post_type !== 'companion_profile') {
        return new WP_Error('not_found', __('Profil bulunamadı.', 'hive-ultra-premium'), array('status' => 404));
    }

    if (is_user_logged_in()) {
        $user = wp_get_current_user();
        $sender_name  = $user->display_name;
        $sender_email = $user->user_email;
        $sender_id    = $user->ID;
    } else {
        $sender_name  = __('Ziyaretçi', 'hive-ultra-premium');
        $sender_email = '';
        $sender_id    = 0;
    }

    $offer = array(
        'user_id'    => $sender_id,
        'user_name'  => $sender_name,
        'user_email' => $sender_email,
        'message'    => $message,
        'time'       => time(),
        'ip'         => isset($_SERVER['REMOTE_ADDR']) ? sanitize_text_field(wp_unslash($_SERVER['REMOTE_ADDR'])) : '',
    );

    $offers = get_post_meta($profile_id, 'hive_offers', true);
    if (!is_array($offers)) {
        $offers = array();
    }
    $offers[] = $offer;
    update_post_meta($profile_id, 'hive_offers', $offers);

    $contact_line = $sender_email
        ? sprintf('%s (%s)', $sender_name, $sender_email)
        : $sender_name;

    $telegram_msg = sprintf(
        "💌 Yeni Teklif — %s\n\n👤 %s\n\n📝 %s\n\n🔗 %s",
        get_the_title($profile_id),
        $contact_line,
        $message,
        get_permalink($profile_id)
    );

    $sent = hive_send_telegram_offer($profile_id, $telegram_msg);

    return rest_ensure_response(array(
        'ok'   => true,
        'sent' => $sent,
    ));
}

/**
 * Telegram bildirimi
 */
function hive_send_telegram_offer($profile_id, $message) {
    $token = get_option('hive_telegram_bot_token', '');
    if (!$token) {
        $token = defined('HIVE_TELEGRAM_BOT_TOKEN') ? HIVE_TELEGRAM_BOT_TOKEN : '';
    }
    if (!$token) {
        return false;
    }

    $chat_id = get_post_meta($profile_id, 'telegram_chat_id', true);
    if (!$chat_id) {
        return false;
    }

    $url = 'https://api.telegram.org/bot' . $token . '/sendMessage';
    $res = wp_remote_post($url, array(
        'timeout' => 15,
        'body'    => array(
            'chat_id'    => $chat_id,
            'text'       => $message,
            'parse_mode' => 'HTML',
        ),
    ));

    if (is_wp_error($res)) {
        return false;
    }
    $code = wp_remote_retrieve_response_code($res);
    return $code >= 200 && $code < 300;
}

/**
 * REST route kayıt
 */
function hive_swipe_register_routes() {
    register_rest_route('hive/v1', '/next-profile', array(
        'methods'             => 'GET',
        'callback'            => 'hive_swipe_next_profiles',
        'permission_callback' => '__return_true',
        'args'                => array(
            'exclude' => array(
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
            ),
        ),
    ));

    register_rest_route('hive/v1', '/swipe', array(
        'methods'             => 'POST',
        'callback'            => 'hive_swipe_record',
        'permission_callback' => '__return_true',
        'args'                => array(
            'profile_id' => array('required' => true, 'type' => 'integer'),
            'action'     => array('required' => true, 'type' => 'string'),
        ),
    ));

    register_rest_route('hive/v1', '/offer', array(
        'methods'             => 'POST',
        'callback'            => 'hive_swipe_send_offer',
        'permission_callback' => '__return_true',
        'args'                => array(
            'profile_id' => array('required' => true, 'type' => 'integer'),
            'message'    => array('required' => true, 'type' => 'string'),
        ),
    ));
}
add_action('rest_api_init', 'hive_swipe_register_routes');

/**
 * Swipe asset'leri — yalnızca ana sayfa
 */
function hive_swipe_enqueue_assets() {
    if (!is_front_page()) {
        return;
    }

    wp_enqueue_style(
        'hive-swipe',
        HIVE_ULTRA_URI . '/assets/css/swipe.css',
        array('hive-ultra-style'),
        HIVE_ULTRA_VERSION
    );

    wp_enqueue_script(
        'hive-swipe-app',
        HIVE_ULTRA_URI . '/assets/js/swipe-app.js',
        array(),
        HIVE_ULTRA_VERSION,
        true
    );

    wp_localize_script('hive-swipe-app', 'hiveSwipeSettings', array(
        'restUrl' => esc_url_raw(rest_url('hive/v1')),
        'nonce'   => wp_create_nonce('wp_rest'),
        'i18n'    => array(
            'like'             => __('Beğen', 'hive-ultra-premium'),
            'dislike'          => __('Geç', 'hive-ultra-premium'),
            'offer'            => __('Teklif Yap', 'hive-ultra-premium'),
            'sendOffer'        => __('Gönder', 'hive-ultra-premium'),
            'offerPlaceholder' => __('Teklifini yaz…', 'hive-ultra-premium'),
            'noProfiles'       => __('Şimdilik başka profil yok. Daha sonra tekrar bakın!', 'hive-ultra-premium'),
            'offerSent'        => __('Teklifiniz gönderildi!', 'hive-ultra-premium'),
            'loading'          => __('Profiller yükleniyor…', 'hive-ultra-premium'),
            'viewProfile'      => __('Profili Gör', 'hive-ultra-premium'),
            'matched'          => __('Eşleşme!', 'hive-ultra-premium'),
        ),
    ));
}
add_action('wp_enqueue_scripts', 'hive_swipe_enqueue_assets', 20);
