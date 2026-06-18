<?php
/**
 * Comments template with star ratings
 *
 * @package Hive_Ultra_Premium
 */

if (post_password_required()) {
    return;
}
?>

<div id="comments" class="hive-comments">
    <?php if (have_comments()) : ?>
        <h2 class="hive-comments-title">
            <?php
            printf(
                esc_html(_n('%d Değerlendirme', '%d Değerlendirme', get_comments_number(), 'hive-ultra-premium')),
                get_comments_number()
            );
            ?>
        </h2>
        <ol class="comment-list">
            <?php
            wp_list_comments(array(
                'style'       => 'ol',
                'short_ping'  => true,
                'avatar_size' => 48,
                'callback'    => 'hive_ultra_comment_callback',
            ));
            ?>
        </ol>
        <?php the_comments_navigation(); ?>
    <?php endif; ?>

    <?php if (comments_open()) : ?>
        <div id="respond" class="comment-respond">
            <h3 id="reply-title" class="comment-reply-title"><?php esc_html_e('Değerlendirme Yap', 'hive-ultra-premium'); ?></h3>
            <form action="<?php echo esc_url(site_url('/wp-comments-post.php')); ?>" method="post" class="hive-comment-form">
                <div class="hive-star-input">
                    <label><?php esc_html_e('Puanınız', 'hive-ultra-premium'); ?></label>
                    <div class="hive-stars-select" data-rating="5">
                        <?php for ($s = 1; $s <= 5; $s++) : ?>
                            <button type="button" class="hive-star-btn" data-value="<?php echo $s; ?>" aria-label="<?php echo esc_attr($s . ' yıldız'); ?>">★</button>
                        <?php endfor; ?>
                    </div>
                    <input type="hidden" name="hive_rating" id="hive-rating-input" value="5" />
                </div>
                <p class="comment-form-comment">
                    <label for="comment"><?php esc_html_e('Yorumunuz', 'hive-ultra-premium'); ?></label>
                    <textarea id="comment" name="comment" rows="4" required></textarea>
                </p>
                <p class="comment-form-author">
                    <label for="author"><?php esc_html_e('İsim', 'hive-ultra-premium'); ?></label>
                    <input id="author" name="author" type="text" required />
                </p>
                <p class="comment-form-email">
                    <label for="email"><?php esc_html_e('E-posta', 'hive-ultra-premium'); ?></label>
                    <input id="email" name="email" type="email" required />
                </p>
                <?php comment_id_fields(); ?>
                <p class="form-submit">
                    <button type="submit" class="btn btn-primary"><?php esc_html_e('Gönder', 'hive-ultra-premium'); ?></button>
                </p>
            </form>
        </div>
    <?php endif; ?>
</div>
