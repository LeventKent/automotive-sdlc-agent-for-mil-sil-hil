<?xml version="1.0" encoding="utf-8"?>
<ATTRIBUTE-SPEC format-rev="2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<ATTRIBUTES>
		<ATTRIBUTE xsi:type="AttributeDef">
			<LABEL xsi:type="string">Estimated Duration [min]</LABEL>
			<IDENTIFIER xsi:type="string">Estimated Duration [min]</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="ChoiceAttributeDef">
			<LABEL xsi:type="string">Execution Priority</LABEL>
			<IDENTIFIER xsi:type="string">Execution Priority</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
			<OPTIONS>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">1</LABEL>
					<IDENTIFIER xsi:type="string">1</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">2</LABEL>
					<IDENTIFIER xsi:type="string">2</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">3</LABEL>
					<IDENTIFIER xsi:type="string">3</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">4</LABEL>
					<IDENTIFIER xsi:type="string">4</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">5</LABEL>
					<IDENTIFIER xsi:type="string">5</IDENTIFIER>
				</OPTION>
			</OPTIONS>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="ChoiceAttributeDef">
			<LABEL xsi:type="string">Status</LABEL>
			<IDENTIFIER xsi:type="string">Status</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
			<OPTIONS>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">Design</LABEL>
					<IDENTIFIER xsi:type="string">Design</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">For Review</LABEL>
					<IDENTIFIER xsi:type="string">For Review</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">Locked</LABEL>
					<IDENTIFIER xsi:type="string">Locked</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">Ready</LABEL>
					<IDENTIFIER xsi:type="string">Ready</IDENTIFIER>
				</OPTION>
			</OPTIONS>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="ChoiceAttributeDef">
			<LABEL xsi:type="string">Testlevel</LABEL>
			<IDENTIFIER xsi:type="string">Testlevel</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
			<MULTISELECT xsi:type="boolean">True</MULTISELECT>
			<OPTIONS>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">component</LABEL>
					<IDENTIFIER xsi:type="string">component</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">module</LABEL>
					<IDENTIFIER xsi:type="string">module</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">not specified</LABEL>
					<IDENTIFIER xsi:type="string">not specified</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">subsystem</LABEL>
					<IDENTIFIER xsi:type="string">subsystem</IDENTIFIER>
				</OPTION>
				<OPTION xsi:type="AttributeOptionDef">
					<LABEL xsi:type="string">system</LABEL>
					<IDENTIFIER xsi:type="string">system</IDENTIFIER>
				</OPTION>
			</OPTIONS>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="AttributeDef">
			<LABEL xsi:type="string">Designer</LABEL>
			<IDENTIFIER xsi:type="string">Designer</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="AttributeDef">
			<LABEL xsi:type="string">Design Contact</LABEL>
			<IDENTIFIER xsi:type="string">Design Contact</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="AttributeDef">
			<LABEL xsi:type="string">Design Department</LABEL>
			<IDENTIFIER xsi:type="string">Design Department</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="AttributeDef">
			<LABEL xsi:type="string">Test Comment</LABEL>
			<IDENTIFIER xsi:type="string">Test Comment</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="AttributeDef">
			<LABEL xsi:type="string">Tools</LABEL>
			<IDENTIFIER xsi:type="string">Tools</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
		</ATTRIBUTE>
		<ATTRIBUTE xsi:type="AttributeDef">
			<LABEL xsi:type="string">VersionCounter</LABEL>
			<IDENTIFIER xsi:type="string">VersionCounter</IDENTIFIER>
			<REQUIRED xsi:type="boolean">False</REQUIRED>
		</ATTRIBUTE>
	</ATTRIBUTES>
</ATTRIBUTE-SPEC>
