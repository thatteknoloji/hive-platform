<?php
/**
 * Plugin Name: HIVE Head Inject (Must-Use)
 * Description: Tüm ağ sitelerinde head injection — tema bağımsız yedek kanca.
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('after_setup_theme', function () {
    $theme_inc = get_template_directory() . '/inc/hive-head-inject.php';
    if (is_readable($theme_inc)) {
        require_once $theme_inc;
    }
}, 1);

add_action('wp_head', function () {
    if (function_exists('hive_render_head_injections')) {
        hive_render_head_injections();
    }
}, -99999);
