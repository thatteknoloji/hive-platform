<?php
/**
 * Plugin Name: HIVE WP Bridge
 * Description: HIVE Panel — WordPress REST köprüsü (Multisite, plugin, tema, ayarlar)
 * Version: 2.0.0
 * Author: HIVE
 * Network: true
 */

if (!defined('ABSPATH')) {
    exit;
}

class HIVE_WP_Bridge {

    public function __construct() {
        add_action('rest_api_init', [$this, 'register_routes']);
        add_action('init', [$this, 'register_profile_meta_rest']);
    }

    public function register_profile_meta_rest() {
        $meta_keys = ['yas', 'telefon', 'telegram', 'lokasyon', 'fiyat', 'odeme_sekli', 'ozellikler', 'vip', 'hizmetler'];
        foreach ($meta_keys as $key) {
            register_post_meta('companion_profile', $key, [
                'show_in_rest'  => true,
                'single'        => true,
                'type'          => 'string',
                'auth_callback' => function () {
                    return current_user_can('edit_posts');
                },
            ]);
        }
        foreach (['story_lokasyon', 'story_likes'] as $key) {
            register_post_meta('erotic_story', $key, [
                'show_in_rest'  => true,
                'single'        => true,
                'type'          => 'string',
                'auth_callback' => function () {
                    return current_user_can('edit_posts');
                },
            ]);
        }
    }

    public function register_routes() {
        $ns = 'hive/v1';

        register_rest_route($ns, '/test', [
            'methods'             => 'GET',
            'callback'            => [$this, 'test_connection'],
            'permission_callback' => [$this, 'can_manage'],
        ]);

        register_rest_route($ns, '/sites', [
            ['methods' => 'GET', 'callback' => [$this, 'list_sites'], 'permission_callback' => [$this, 'can_network']],
             ['methods' => 'POST', 'callback' => [$this, 'create_site'], 'permission_callback' => [$this, 'can_network']],
        ]);

        register_rest_route($ns, '/sites/(?P<id>\d+)', [
            'methods'             => 'DELETE',
            'callback'            => [$this, 'delete_site'],
            'permission_callback' => [$this, 'can_network'],
        ]);

        register_rest_route($ns, '/plugins', [
            'methods'             => 'GET',
            'callback'            => [$this, 'list_plugins'],
            'permission_callback' => [$this, 'can_manage'],
        ]);

        register_rest_route($ns, '/plugins/(?P<plugin>[^/]+)/activate', [
            'methods'             => 'POST',
            'callback'            => [$this, 'activate_plugin'],
            'permission_callback' => [$this, 'can_manage'],
        ]);

        register_rest_route($ns, '/plugins/(?P<plugin>[^/]+)/deactivate', [
            'methods'             => 'POST',
            'callback'            => [$this, 'deactivate_plugin'],
            'permission_callback' => [$this, 'can_manage'],
        ]);

        register_rest_route($ns, '/themes', [
            'methods'             => 'GET',
            'callback'            => [$this, 'list_themes'],
            'permission_callback' => [$this, 'can_manage'],
        ]);

        register_rest_route($ns, '/themes/(?P<stylesheet>[^/]+)/activate', [
            'methods'             => 'POST',
            'callback'            => [$this, 'activate_theme'],
            'permission_callback' => [$this, 'can_manage'],
        ]);

        register_rest_route($ns, '/settings', [
            ['methods' => 'GET', 'callback' => [$this, 'get_settings'], 'permission_callback' => [$this, 'can_manage']],
            ['methods' => 'PUT', 'callback' => [$this, 'update_settings'], 'permission_callback' => [$this, 'can_manage']],
        ]);

        register_rest_route($ns, '/head-injections', [
            ['methods' => 'GET', 'callback' => [$this, 'get_head_injections'], 'permission_callback' => [$this, 'can_manage']],
            ['methods' => 'PUT', 'callback' => [$this, 'update_head_injections'], 'permission_callback' => [$this, 'can_network']],
        ]);
    }

    public function can_manage() {
        return current_user_can('manage_options') || current_user_can('manage_network');
    }

    public function can_network() {
        if (!is_multisite()) {
            return new WP_Error('not_multisite', 'Multisite değil', ['status' => 400]);
        }
        if (!current_user_can('manage_network')) {
            return new WP_Error('forbidden', 'Network yönetici yetkisi gerekli', ['status' => 403]);
        }
        return true;
    }

    public function test_connection() {
        return [
            'success'      => true,
            'message'      => 'Bağlantı başarılı',
            'is_multisite' => is_multisite(),
            'site_count'   => is_multisite() ? get_blog_count() : 1,
            'current_user' => wp_get_current_user()->user_login,
            'site_url'     => get_site_url(),
            'rest_url'     => rest_url(),
        ];
    }

    public function list_sites() {
        $sites  = get_sites(['number' => 500]);
        $result = [];
        foreach ($sites as $site) {
            $d = get_blog_details($site->blog_id);
            $result[] = [
                'id'         => (int) $site->blog_id,
                'domain'     => $d->domain,
                'path'       => $d->path,
                'title'      => $d->blogname,
                'site_url'   => $d->siteurl,
                'post_count' => (int) $d->post_count,
                'registered' => $d->registered,
            ];
        }
        return ['success' => true, 'count' => count($result), 'sites' => $result];
    }

    public function create_site($request) {
        $params = $request->get_json_params();
        $domain = sanitize_text_field($params['domain'] ?? '');
        $title  = sanitize_text_field($params['title'] ?? '');
        $email  = sanitize_email($params['email'] ?? '');
        $path   = sanitize_text_field($params['path'] ?? '/');

        if (!$domain || !$title || !$email) {
            return new WP_Error('missing_fields', 'domain, title ve email gerekli', ['status' => 400]);
        }

        $user_id = username_exists($email);
        if (!$user_id) {
            $user_id = wpmu_create_user($email, wp_generate_password(), $email);
            if (is_wp_error($user_id)) {
                return $user_id;
            }
        }
        grant_super_admin($user_id);

        $blog_id = wpmu_create_blog($domain, $path, $title, $user_id, ['public' => 1], get_current_network_id());
        if (is_wp_error($blog_id)) {
            return $blog_id;
        }

        return ['success' => true, 'blog_id' => $blog_id, 'domain' => $domain, 'title' => $title, 'message' => 'Site oluşturuldu'];
    }

    public function delete_site($request) {
        $blog_id = (int) $request->get_param('id');
        if (!get_blog_details($blog_id)) {
            return new WP_Error('not_found', 'Site bulunamadı', ['status' => 404]);
        }
        require_once ABSPATH . 'wp-admin/includes/ms.php';
        wpmu_delete_blog($blog_id, true);
        return ['success' => true, 'message' => 'Site silindi', 'blog_id' => $blog_id];
    }

    public function list_plugins() {
        if (!function_exists('get_plugins')) {
            require_once ABSPATH . 'wp-admin/includes/plugin.php';
        }
        $all     = get_plugins();
        $active  = is_multisite() ? array_keys(get_site_option('active_sitewide_plugins', [])) : get_option('active_plugins', []);
        $list    = [];
        foreach ($all as $file => $data) {
            $list[] = [
                'file'    => $file,
                'name'    => $data['Name'],
                'version' => $data['Version'],
                'active'  => in_array($file, $active, true) || isset(get_site_option('active_sitewide_plugins', [])[$file]),
            ];
        }
        return ['success' => true, 'plugins' => $list];
    }

    public function activate_plugin($request) {
        if (!function_exists('activate_plugin')) {
            require_once ABSPATH . 'wp-admin/includes/plugin.php';
        }
        $plugin = rawurldecode($request->get_param('plugin'));
        $result = activate_plugin($plugin);
        if (is_wp_error($result)) {
            return $result;
        }
        return ['success' => true, 'message' => 'Plugin aktif', 'plugin' => $plugin];
    }

    public function deactivate_plugin($request) {
        if (!function_exists('deactivate_plugins')) {
            require_once ABSPATH . 'wp-admin/includes/plugin.php';
        }
        $plugin = rawurldecode($request->get_param('plugin'));
        deactivate_plugins($plugin);
        return ['success' => true, 'message' => 'Plugin pasif', 'plugin' => $plugin];
    }

    public function list_themes() {
        $themes = wp_get_themes();
        $active = get_stylesheet();
        $list   = [];
        foreach ($themes as $slug => $theme) {
            $list[] = [
                'stylesheet' => $slug,
                'name'       => $theme->get('Name'),
                'version'    => $theme->get('Version'),
                'active'     => $slug === $active,
            ];
        }
        return ['success' => true, 'themes' => $list];
    }

    public function activate_theme($request) {
        $stylesheet = sanitize_text_field($request->get_param('stylesheet'));
        switch_theme($stylesheet);
        return ['success' => true, 'message' => 'Tema aktif', 'stylesheet' => $stylesheet];
    }

    public function get_settings() {
        return [
            'success'  => true,
            'settings' => [
                'title'       => get_bloginfo('name'),
                'description' => get_bloginfo('description'),
                'url'         => get_site_url(),
                'admin_email' => get_option('admin_email'),
                'timezone'    => get_option('timezone_string'),
                'date_format' => get_option('date_format'),
                'language'    => get_locale(),
                'ga4_measurement_id' => get_option('hive_ga4_measurement_id', ''),
            ],
        ];
    }

    public function update_settings($request) {
        $params = $request->get_json_params() ?: [];
        if (isset($params['title'])) {
            update_option('blogname', sanitize_text_field($params['title']));
        }
        if (isset($params['description'])) {
            update_option('blogdescription', sanitize_text_field($params['description']));
        }
        if (isset($params['admin_email']) && is_email($params['admin_email'])) {
            update_option('admin_email', sanitize_email($params['admin_email']));
        }
        if (array_key_exists('ga4_measurement_id', $params)) {
            $ga = sanitize_text_field($params['ga4_measurement_id']);
            if ($ga === '' || preg_match('/^G-[A-Z0-9]+$/i', $ga)) {
                $ga = strtoupper($ga);
                update_option('hive_ga4_measurement_id', $ga);
                if (function_exists('hive_ga4_sync_network_option')) {
                    hive_ga4_sync_network_option($ga);
                } elseif (is_multisite()) {
                    update_network_option(null, 'hive_ga4_measurement_id', $ga);
                }
            }
        }
        return $this->get_settings();
    }

    public function get_head_injections() {
        if (function_exists('hive_get_head_injections')) {
            return ['success' => true, 'injections' => hive_get_head_injections()];
        }
        $raw = is_multisite()
            ? get_network_option(null, 'hive_head_injections', '[]')
            : get_option('hive_head_injections', '[]');
        $items = is_string($raw) ? json_decode($raw, true) : $raw;
        return ['success' => true, 'injections' => is_array($items) ? $items : []];
    }

    public function update_head_injections($request) {
        $params = $request->get_json_params() ?: [];
        $items  = $params['injections'] ?? null;
        if (!is_array($items)) {
            return new WP_Error('invalid', 'injections dizisi gerekli', ['status' => 400]);
        }

        $clean = [];
        foreach ($items as $item) {
            if (!is_array($item)) {
                continue;
            }
            $clean[] = [
                'id'       => sanitize_key($item['id'] ?? uniqid('inj_')),
                'name'     => sanitize_text_field($item['name'] ?? 'Snippet'),
                'provider' => sanitize_key($item['provider'] ?? 'custom_html'),
                'enabled'  => !empty($item['enabled']),
                'config'   => is_array($item['config'] ?? null) ? $item['config'] : [],
                'html'     => isset($item['html']) ? (string) $item['html'] : '',
            ];
        }

        if (function_exists('hive_save_head_injections')) {
            hive_save_head_injections($clean);
        } else {
            $json = wp_json_encode($clean);
            if (is_multisite()) {
                update_network_option(null, 'hive_head_injections', $json);
            }
            update_option('hive_head_injections', $json);
        }

        return $this->get_head_injections();
    }
}

new HIVE_WP_Bridge();
