odoo.define("zbs.mapper.redirect.at_list", function (require) {
	"use strict";

	var ListRenderer = require("web.ListRenderer");
	ListRenderer.include({
		_renderRow: function (record) {
			let row = this._super(record);
			var self = this;
			//if (!record.context.no_js_click && record.model == "zbs.mapping") {
			if (record.model == "zbs.mapping") {
				row.addClass('o_list_no_open');
				// add click event
				row.bind({
					click: function (ev) {
						var $target = $(ev.target);
						if ($target[0].tagName === "BUTTON") {
							return;
						}
						if (ev.shiftKey || ev.altKey) {
							ev.preventDefault();
							ev.stopPropagation();
							self._rpc({
								model: record.model,
								method: 'open_mapping',
								args: [record.data.id],
							}).then(function (action) {
								console.log(action);
								self.do_action(action, {
									on_close: function() {
										self.trigger_up('reload');
									},
								})
							});
						}
					}
				});
			}
			return row
		},
	});
});