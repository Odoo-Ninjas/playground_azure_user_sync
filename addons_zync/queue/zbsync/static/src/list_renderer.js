odoo.define("zbs.redirect.at_list", function (require) {
	"use strict";

	var ListRenderer = require("web.ListRenderer");
	ListRenderer.include({
		_renderRow: function (record) {
			let row = this._super(record);
			var self = this;
			if (record.model == "zbs.instance.line" || record.model == "zbs.pipeline.line") {
				row.addClass('o_list_no_open');
				// add click event
				row.bind({
					click: function (ev) {
						var $target = $(ev.target);
						if ($target[0].tagName === "BUTTON") {
							return;
						}
						ev.preventDefault();
						ev.stopPropagation();
						if ($target.hasClass("open_line")) {
							self._rpc({
								model: record.model,
								method: 'open_line',
								args: [record.data.id],
								kwargs: {
									'css_class': $(ev.target).prop('class'),
								},
							}).then(function (action) {
								console.log(action);
								self.do_action(action, {
									on_close: function() {
										self.trigger_up('reload');
									},
								})
							});
						}
						else {
							self._rpc({
								model: record.data.worker_id.model,
								method: 'open_action',
								args: [record.data.worker_id.res_id],
							}).then(function (action) {
								console.log(action);
								self.do_action(action)
							});
						}
					}
				});
			}
			return row
		},
	});
});