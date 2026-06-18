<?php
/**
 * Yasal sayfalar — Sorumluluk Reddi, Gizlilik, Kullanım Şartları
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Yasal sayfa URL (subdomain → ana site)
 */
function hive_legal_page_url($slug) {
    $fetch = function () use ($slug) {
        $page = get_page_by_path($slug);
        return $page ? get_permalink($page) : home_url('/' . $slug . '/');
    };

    if (is_multisite() && !hive_is_main_site()) {
        switch_to_blog(1);
        $url = $fetch();
        restore_current_blog();
        return $url;
    }

    return $fetch();
}

/**
 * Sorumluluk reddi içeriği
 */
function hive_disclaimer_content() {
    ob_start();
    ?>
    <h2><?php esc_html_e('SORUMLULUK REDDİ', 'hive-ultra-premium'); ?></h2>

    <h3>1. <?php esc_html_e('İÇERİK AMACI', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Bu web sitesi (balkutusu.com) ve bağlı alt alan adları (subdomain\'ler) yalnızca bilgilendirme ve rehberlik amacıyla hizmet vermektedir. Sitede yer alan kullanıcı profilleri, açıklamalar ve ilanlar, kullanıcılar tarafından eklenmekte olup, sitenin işletmesi bu içeriklerin doğruluğu, güvenilirliği veya yasallığı konusunda herhangi bir garanti vermemektedir.', 'hive-ultra-premium'); ?></p>

    <h3>2. <?php esc_html_e('ARACILIK YOK', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Bu platform, kullanıcılar arasında doğrudan iletişim kurulmasına olanak tanıyan bir ilan panosu ve rehber niteliğindedir. İşletme, kullanıcılar arasında gerçekleşen herhangi bir iletişim, randevulaşma, ödeme veya diğer işlemler için ARACILIK ETMEZ, KOMİSYON ALMAZ veya ORGANİZASYON YAPMAZ. Kullanıcılar kendi aralarındaki iletişim ve işlemlerden bizzat sorumludur.', 'hive-ultra-premium'); ?></p>

    <h3>3. <?php esc_html_e('YAŞ SINIRI', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Bu siteye erişen ve içerikleri kullanan tüm ziyaretçilerin 18 (onsekiz) yaşını doldurduğunu peşinen kabul eder. 18 yaşından küçüklerin siteyi kullanması kesinlikle yasaktır.', 'hive-ultra-premium'); ?></p>

    <h3>4. <?php esc_html_e('YASAL UYUMLULUK', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Kullanıcılar, siteyi kullanırken bulundukları ülkenin, eyaletin veya bölgenin tüm geçerli yasalarına ve düzenlemelerine uymakla yükümlüdür. İşletme, kullanıcıların yasalara aykırı faaliyetlerinden sorumlu tutulamaz.', 'hive-ultra-premium'); ?></p>

    <h3>5. <?php esc_html_e('ÜÇÜNCÜ TARAF BAĞLANTILARI', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Site, üçüncü şahıslara ait web sitelerine bağlantılar içerebilir. Bu bağlantı sitelerinin içeriği üzerinde hiçbir kontrolümüz yoktur ve bu sitelerin içeriklerinden veya gizlilik uygulamalarından sorumlu değiliz.', 'hive-ultra-premium'); ?></p>

    <h3>6. <?php esc_html_e('HİZMET SAĞLAYICI STATÜSÜ', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Bu site, 5651 sayılı Kanun ve ilgili mevzuat kapsamında "barındırıcı" statüsünde faaliyet göstermektedir. Yasa dışı içerik bildirimleri üzerine içerik 24 saat içinde incelenir ve kaldırılır.', 'hive-ultra-premium'); ?></p>

    <h3>7. <?php esc_html_e('DEĞİŞİKLİK HAKKI', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('İşletme, bu sorumluluk reddi metnini herhangi bir zamanda ve önceden bildirimde bulunmaksızın değiştirme hakkını saklı tutar.', 'hive-ultra-premium'); ?></p>

    <h3>8. <?php esc_html_e('İLETİŞİM', 'hive-ultra-premium'); ?></h3>
    <p><?php
        printf(
            /* translators: %s: email address */
            esc_html__('Bu metinle ilgili sorularınız veya şikayetleriniz için bize şu adresten ulaşabilirsiniz: %s', 'hive-ultra-premium'),
            '<a href="mailto:info@balkutusu.com">info@balkutusu.com</a>'
        );
    ?></p>

    <p><em><?php esc_html_e('Son güncelleme: 07.06.2026', 'hive-ultra-premium'); ?></em></p>
    <?php
    return ob_get_clean();
}

/**
 * Gizlilik politikası (özet)
 */
function hive_privacy_content() {
    ob_start();
    ?>
    <p><?php esc_html_e('Bal Kutusu (balkutusu.com) olarak ziyaretçi gizliliğine saygı duyuyoruz. Bu politika, sitede toplanan verilerin nasıl işlendiğini açıklar.', 'hive-ultra-premium'); ?></p>
    <h3><?php esc_html_e('Toplanan Veriler', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Teknik loglar (IP, tarayıcı bilgisi), çerezler ve gönüllü iletişim formları aracılığıyla paylaştığınız bilgiler işlenebilir.', 'hive-ultra-premium'); ?></p>
    <h3><?php esc_html_e('Kullanım Amacı', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Veriler site güvenliği, performans analizi ve yasal yükümlülüklerin yerine getirilmesi amacıyla kullanılır. Üçüncü taraflarla izinsiz paylaşım yapılmaz.', 'hive-ultra-premium'); ?></p>
    <h3><?php esc_html_e('İletişim', 'hive-ultra-premium'); ?></h3>
    <p><?php printf(esc_html__('Gizlilik talepleri için: %s', 'hive-ultra-premium'), '<a href="mailto:info@balkutusu.com">info@balkutusu.com</a>'); ?></p>
    <p><em><?php esc_html_e('Son güncelleme: 07.06.2026', 'hive-ultra-premium'); ?></em></p>
    <?php
    return ob_get_clean();
}

/**
 * Kullanım şartları (özet)
 */
function hive_terms_content() {
    ob_start();
    ?>
    <p><?php esc_html_e('balkutusu.com sitesini kullanarak aşağıdaki şartları kabul etmiş sayılırsınız.', 'hive-ultra-premium'); ?></p>
    <h3><?php esc_html_e('Kullanım Koşulları', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Site yalnızca 18 yaş ve üzeri yetişkinler içindir. İçerikler bilgilendirme amaçlıdır; kullanıcılar yerel yasalara uymakla yükümlüdür.', 'hive-ultra-premium'); ?></p>
    <h3><?php esc_html_e('Yasaklı Kullanım', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Yasa dışı içerik paylaşımı, spam, kötüye kullanım ve site altyapısına zarar verecek faaliyetler yasaktır.', 'hive-ultra-premium'); ?></p>
    <h3><?php esc_html_e('Sorumluluk', 'hive-ultra-premium'); ?></h3>
    <p><?php esc_html_e('Platform aracılık etmez; kullanıcılar arası işlemlerden işletme sorumlu değildir. Detaylar için Sorumluluk Reddi sayfasına bakınız.', 'hive-ultra-premium'); ?></p>
    <p><em><?php esc_html_e('Son güncelleme: 07.06.2026', 'hive-ultra-premium'); ?></em></p>
    <?php
    return ob_get_clean();
}

/**
 * Yasal sayfaları oluştur / güncelle (ana site)
 */
function hive_seed_legal_pages() {
    if (is_multisite() && get_current_blog_id() !== 1) {
        return;
    }

    $pages = array(
        'sorumluluk-reddi' => array(
            'title'   => __('Sorumluluk Reddi', 'hive-ultra-premium'),
            'content' => hive_disclaimer_content(),
        ),
        'gizlilik-politikasi' => array(
            'title'   => __('Gizlilik Politikası', 'hive-ultra-premium'),
            'content' => hive_privacy_content(),
        ),
        'kullanim-sartlari' => array(
            'title'   => __('Kullanım Şartları', 'hive-ultra-premium'),
            'content' => hive_terms_content(),
        ),
    );

    foreach ($pages as $slug => $data) {
        $existing = get_page_by_path($slug);
        if ($existing) {
            wp_update_post(array(
                'ID'           => $existing->ID,
                'post_title'   => $data['title'],
                'post_content' => $data['content'],
                'post_status'  => 'publish',
            ));
            continue;
        }
        wp_insert_post(array(
            'post_type'    => 'page',
            'post_status'  => 'publish',
            'post_title'   => $data['title'],
            'post_name'    => $slug,
            'post_content' => $data['content'],
        ));
    }
}

add_action('after_switch_theme', 'hive_seed_legal_pages');
add_action('init', function () {
    if (!get_option('hive_legal_pages_v1')) {
        hive_seed_legal_pages();
        update_option('hive_legal_pages_v1', 1);
    }
}, 20);
